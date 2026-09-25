import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.stt_benchmark.contracts.evaluator import EvaluatorInput
from app.stt_benchmark.evaluation_orchestrator import EvaluationOrchestrator
from app.stt_benchmark.evaluators.contract import (
    EvaluatorFailure,
    EvaluatorSettings,
    NativeEvaluatorOutput,
    SupportDecision,
)
from app.stt_benchmark.evaluators.registry import EvaluatorRegistry
from app.stt_benchmark.storage.artifacts import EvaluationArtifactStore


def evaluator_input() -> EvaluatorInput:
    return EvaluatorInput(
        experiment_id="verbatim-001",
        sample_id="filler-001",
        prediction_id="prediction-fixed",
        gold_version="gold-v1",
        prediction_version="prediction-v1",
        gold_text="Um I I wan- wanted that.",
        prediction_text="Um I wanted that.",
        expected_behavior="transcribe",
        observed_status="transcribed",
        language="en",
        duration_seconds=2.0,
        latency_ms=10,
        model="fake/model",
        prompt_version="prompt-v1",
        legacy_dataset_version="stt-eval-v1",
    )


@dataclass
class ConcurrencyCounter:
    active: int = 0
    maximum: int = 0


class RecordingEvaluator:
    evaluator_version = "test-v1"
    normalization_profile = "raw-test-v1"
    required_inputs = frozenset({"gold_text", "prediction_text"})
    supported_metrics = frozenset({"test"})

    def __init__(
        self,
        evaluator_id: str,
        *,
        counter: ConcurrencyCounter | None = None,
        failure: bool = False,
        unsupported: bool = False,
        support_failure: bool = False,
    ) -> None:
        self.evaluator_id = evaluator_id
        self.counter = counter
        self.failure = failure
        self.unsupported = unsupported
        self.support_failure = support_failure

    def supports(self, _evaluator_input: EvaluatorInput) -> SupportDecision:
        if self.support_failure:
            raise RuntimeError("support check failed")
        if self.unsupported:
            return SupportDecision.no("missing_input:timestamps")
        return SupportDecision.yes()

    async def evaluate(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        if self.failure:
            raise EvaluatorFailure("isolated_test_failure")
        if self.counter:
            self.counter.active += 1
            self.counter.maximum = max(self.counter.maximum, self.counter.active)
        await asyncio.sleep(0.02)
        if self.counter:
            self.counter.active -= 1
        payload = json.dumps(
            {"native": self.evaluator_id, "prediction": evaluator_input.prediction_text}
        ).encode()
        return NativeEvaluatorOutput(payload, ".json", "application/json")


@pytest.mark.asyncio
async def test_selected_evaluators_run_in_parallel_and_store_native_outputs(tmp_path: Path) -> None:
    counter = ConcurrencyCounter()
    registry = EvaluatorRegistry(
        [
            RecordingEvaluator("first", counter=counter),
            RecordingEvaluator("second", counter=counter),
            RecordingEvaluator("not-selected", counter=counter),
        ]
    )
    store = EvaluationArtifactStore(tmp_path, "evaluation-001")
    orchestrator = EvaluationOrchestrator(
        registry,
        EvaluatorSettings(("first", "second"), max_concurrency=2),
        store,
    )

    index = await orchestrator.run((evaluator_input(),), "evaluation-001")

    assert counter.maximum == 2
    assert [item.evaluator_id for item in index.executions] == ["first", "second"]
    assert all(item.status == "success" for item in index.executions)
    for execution in index.executions:
        result_path = store.run_directory / execution.raw_result_path
        assert json.loads(result_path.read_text())["native"] == execution.evaluator_id
        assert execution.raw_result_sha256
    stored_index = json.loads((store.run_directory / "index.json").read_text())
    assert stored_index["schemaVersion"] == "stt-evaluator-index-v2"
    assert stored_index["enabledEvaluators"] == ["first", "second"]
    assert stored_index["executions"][0]["goldVersionSource"] == "dataset-version-fallback"
    assert stored_index["executions"][0]["goldReviewStatus"] == "unknown"
    assert stored_index["executions"][0]["goldSha256"] == hashlib.sha256(
        evaluator_input().gold_text.encode("utf-8")
    ).hexdigest()
    assert "goldText" not in stored_index["executions"][0]


@pytest.mark.asyncio
async def test_failure_and_unsupported_are_isolated(tmp_path: Path) -> None:
    registry = EvaluatorRegistry(
        [
            RecordingEvaluator("working"),
            RecordingEvaluator("broken", failure=True),
            RecordingEvaluator("needs-time", unsupported=True),
            RecordingEvaluator("broken-support", support_failure=True),
        ]
    )
    orchestrator = EvaluationOrchestrator(
        registry,
        EvaluatorSettings(registry.ids, max_concurrency=4),
        EvaluationArtifactStore(tmp_path, "evaluation-002"),
    )

    index = await orchestrator.run((evaluator_input(),), "evaluation-002")
    statuses = {item.evaluator_id: item.status for item in index.executions}
    reasons = {item.evaluator_id: item.reason for item in index.executions}

    assert statuses == {
        "working": "success",
        "broken": "failed",
        "needs-time": "unsupported",
        "broken-support": "failed",
    }
    assert reasons["broken"] == "isolated_test_failure"
    assert reasons["needs-time"] == "missing_input:timestamps"
    assert reasons["broken-support"] == "evaluator_support_check_failed:RuntimeError"


@pytest.mark.asyncio
async def test_same_prediction_can_be_evaluated_again_without_overwrite(tmp_path: Path) -> None:
    registry = EvaluatorRegistry([RecordingEvaluator("working")])
    settings = EvaluatorSettings(("working",), max_concurrency=1)

    first = await EvaluationOrchestrator(
        registry,
        settings,
        EvaluationArtifactStore(tmp_path, "rerun-001"),
    ).run((evaluator_input(),), "rerun-001")
    revised_gold = evaluator_input().model_copy(
        update={"gold_text": evaluator_input().gold_text + " uh"}
    )
    second = await EvaluationOrchestrator(
        registry,
        settings,
        EvaluationArtifactStore(tmp_path, "rerun-002"),
    ).run((revised_gold,), "rerun-002")

    assert first.executions[0].prediction_id == second.executions[0].prediction_id
    assert first.executions[0].gold_version == second.executions[0].gold_version
    assert first.executions[0].gold_sha256 != second.executions[0].gold_sha256
    assert first.executions[0].prediction_sha256 == second.executions[0].prediction_sha256
    assert (tmp_path / "rerun-001" / "index.json").is_file()
    assert (tmp_path / "rerun-002" / "index.json").is_file()
