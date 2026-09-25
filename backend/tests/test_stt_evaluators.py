import asyncio
import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.stt_benchmark.contracts.dataset import TranscriptionDataset, TranscriptionSample
from app.stt_benchmark.contracts.evaluator import (
    EvaluationSupplement,
    EvaluationSupplements,
    EvaluatorInput,
    TranscriptSegment,
)
from app.stt_benchmark.contracts.run import (
    TranscriptionObservation,
    TranscriptionRun,
    TranscriptionRunConfig,
)
from app.stt_benchmark.evaluator_inputs import build_evaluator_inputs
from app.stt_benchmark.evaluators.custom import CustomEvaluator
from app.stt_benchmark.evaluators.huggingface_evaluate import HuggingFaceEvaluateEvaluator
from app.stt_benchmark.evaluators.jiwer_evaluator import JiwerEvaluator
from app.stt_benchmark.evaluators.meeteval_evaluator import MeetEvalEvaluator
from app.stt_benchmark.evaluators.nyra import NyraEvaluator
from app.stt_benchmark.evaluators.sctk import SctkEvaluator


def verbatim_input() -> EvaluatorInput:
    return EvaluatorInput(
        experiment_id="verbatim-001",
        sample_id="filler-fragment-001",
        prediction_id="prediction-001",
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


def test_input_builder_preserves_raw_gold_and_prediction_text() -> None:
    gold = "Um,\nI I wan- wanted THAT."
    prediction = "um...\nI wanted that"
    dataset = TranscriptionDataset(
        version="stt-eval-v1",
        samples=[
            TranscriptionSample(
                id="raw-text-001",
                audio_path="samples/raw-text-001.wav",
                reference_transcript=gold,
                tags=["filler", "fragment", "repetition"],
                duration_seconds=2.0,
                source="synthetic",
                expected_behavior="transcribe",
            )
        ],
    )
    run = TranscriptionRun(
        experiment_id="raw-text-run",
        dataset_version="stt-eval-v1",
        model="fake/model",
        prompt_version="prompt-v1",
        created_at="2026-09-25T00:00:00Z",
        config=TranscriptionRunConfig(),
        observations=[
            TranscriptionObservation(
                sample_id="raw-text-001",
                status="transcribed",
                transcript=prediction,
                latency_ms=1,
            )
        ],
    )
    supplements = EvaluationSupplements(
        samples=(
            EvaluationSupplement(
                sample_id="raw-text-001",
                gold_version="gold-v2",
                prediction_version="prediction-v3",
                gold_intended_text="I wanted that.",
            ),
        )
    )

    value = build_evaluator_inputs(dataset, run, supplements)[0]

    assert value.gold_text == gold
    assert value.prediction_text == prediction
    assert value.gold_version == "gold-v2"
    assert value.prediction_version == "prediction-v3"


@pytest.mark.asyncio
async def test_custom_evaluator_preserves_existing_metric_meanings() -> None:
    output = await CustomEvaluator().evaluate(verbatim_input())
    result = json.loads(output.payload)

    assert result["wordErrors"] == 2
    assert result["filler"]["referenceItems"] == 1
    assert result["filler"]["matchedItems"] == 1
    assert result["repetition"]["referenceItems"] == 1
    assert result["repetition"]["matchedItems"] == 0


class FakeMetric:
    def __init__(self, name: str) -> None:
        self.name = name

    def compute(self, **_arguments: object) -> dict[str, float]:
        return {self.name: 0.25}


@pytest.mark.asyncio
async def test_huggingface_adapter_preserves_each_metric_native_mapping() -> None:
    evaluator = HuggingFaceEvaluateEvaluator(loader=lambda name: FakeMetric(name))

    output = await evaluator.evaluate(verbatim_input())

    assert json.loads(output.payload) == {"wer": {"wer": 0.25}, "cer": {"cer": 0.25}}


def test_huggingface_reports_empty_reference_as_unsupported() -> None:
    value = verbatim_input().model_copy(update={"gold_text": ""})

    support = HuggingFaceEvaluateEvaluator(loader=lambda name: FakeMetric(name)).supports(value)

    assert not support.supported
    assert support.reason == "empty_reference_not_supported:huggingface-wer"


def test_external_tools_report_missing_dependencies_as_unsupported(tmp_path) -> None:
    value = verbatim_input()
    assert not SctkEvaluator(tmp_path / "missing-sclite").supports(value).supported
    assert not NyraEvaluator(tmp_path / "missing-nyra").supports(value).supported


def test_meeteval_reports_incomplete_segment_inputs_as_unsupported() -> None:
    value = verbatim_input().model_copy(
        update={
            "reference_segments": (
                TranscriptSegment(
                    words="hello", speaker="a", start_time=0.0, end_time=0.5
                ),
            ),
            "prediction_segments": (TranscriptSegment(words="hello", speaker="a"),),
        }
    )

    support = MeetEvalEvaluator().supports(value)

    assert not support.supported
    assert support.reason == "meeteval_segments_have_incomplete_timestamps"


def test_meeteval_reports_missing_speakers_as_unsupported() -> None:
    value = verbatim_input().model_copy(
        update={
            "reference_segments": (TranscriptSegment(words="hello"),),
            "prediction_segments": (TranscriptSegment(words="hello"),),
        }
    )

    support = MeetEvalEvaluator().supports(value)

    assert not support.supported
    assert support.reason == "meeteval_segments_require_speaker_labels"


@dataclass
class FakeMeetEvalRate:
    errors: int = 1
    length: int = 4
    insertions: int = 0
    deletions: int = 1
    substitutions: int = 0


@pytest.mark.asyncio
async def test_meeteval_adapter_selects_time_constrained_mode(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def tcp_word_error_rate(reference, hypothesis, *, collar):
        captured.update(reference=reference, hypothesis=hypothesis, collar=collar)
        return FakeMeetEvalRate()

    fake_module = SimpleNamespace(
        wer=SimpleNamespace(
            wer=SimpleNamespace(
                siso=SimpleNamespace(siso_word_error_rate=lambda *_args: FakeMeetEvalRate()),
                cp=SimpleNamespace(cp_word_error_rate=lambda *_args: FakeMeetEvalRate()),
                time_constrained=SimpleNamespace(tcp_word_error_rate=tcp_word_error_rate),
            )
        )
    )
    monkeypatch.setitem(sys.modules, "meeteval", fake_module)
    monkeypatch.setattr(
        "app.stt_benchmark.evaluators.meeteval_evaluator.importlib.util.find_spec",
        lambda _name: object(),
    )
    segment = TranscriptSegment(
        words="hello there", speaker="speaker-1", start_time=0.2, end_time=1.0
    )
    value = verbatim_input().model_copy(
        update={"reference_segments": (segment,), "prediction_segments": (segment,)}
    )

    output = await MeetEvalEvaluator(collar_seconds=0.5).evaluate(value)
    result = json.loads(output.payload)

    assert result["mode"] == "tcpwer"
    assert result["result"]["deletions"] == 1
    assert captured["collar"] == 0.5
    assert captured["reference"][0]["speaker"] == "speaker-1"


@pytest.mark.external_integration
@pytest.mark.asyncio
async def test_jiwer_real_library_keeps_verbatim_tokens_in_alignment() -> None:
    if importlib.util.find_spec("jiwer") is None:
        pytest.skip("jiwer optional dependency is not installed")
    output = await JiwerEvaluator().evaluate(verbatim_input())
    result = json.loads(output.payload)

    assert result["word"]["references"][0] == ["Um", "I", "I", "wan-", "wanted", "that."]
    assert result["word"]["deletions"] == 2
    assert result["character"]["cer"] > 0


@pytest.mark.external_integration
@pytest.mark.asyncio
async def test_meeteval_real_library_runs_siso() -> None:
    if importlib.util.find_spec("meeteval") is None:
        pytest.skip("meeteval optional dependency is not installed")
    output = await MeetEvalEvaluator().evaluate(verbatim_input())
    result = json.loads(output.payload)

    assert result["mode"] == "siso_wer"
    assert result["result"]["deletions"] == 2


@pytest.mark.network_integration
@pytest.mark.asyncio
async def test_huggingface_real_metrics_load_from_the_hub(tmp_path: Path) -> None:
    if os.getenv("RUN_HUGGINGFACE_INTEGRATION") != "1":
        pytest.skip("set RUN_HUGGINGFACE_INTEGRATION=1 to download official metric modules")
    evaluator = HuggingFaceEvaluateEvaluator(cache_directory=tmp_path)
    first, second = await asyncio.gather(
        evaluator.evaluate(verbatim_input()),
        evaluator.evaluate(
            verbatim_input().model_copy(
                update={"sample_id": "filler-fragment-002", "prediction_id": "prediction-002"}
            )
        ),
    )
    result = json.loads(first.payload)

    assert result["wer"] > 0
    assert result["cer"] > 0
    assert json.loads(second.payload) == result


@pytest.mark.external_integration
@pytest.mark.asyncio
async def test_nyra_official_checkout_runs_through_subprocess_bridge() -> None:
    checkout = os.getenv("NYRA_BENCHMARK_CHECKOUT")
    if not checkout:
        pytest.skip("set NYRA_BENCHMARK_CHECKOUT to the official source checkout")
    value = verbatim_input().model_copy(
        update={
            "gold_intended_text": "I wanted that.",
            "prediction_intended_text": "I wanted that.",
        }
    )

    output = await NyraEvaluator(Path(checkout)).evaluate(value)

    assert "vWER" in json.loads(output.payload)


@pytest.mark.external_integration
@pytest.mark.asyncio
async def test_sctk_official_sclite_binary_produces_native_report() -> None:
    executable = os.getenv("SCTK_EXECUTABLE")
    if not executable:
        pytest.skip("set SCTK_EXECUTABLE to an official sclite binary")

    output = await SctkEvaluator(Path(executable)).evaluate(verbatim_input())

    assert output.media_type == "text/plain"
    assert b"Percent Total Error" in output.payload
