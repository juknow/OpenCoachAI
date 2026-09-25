import asyncio
from datetime import UTC, datetime

from app.stt_benchmark.contracts.evaluator import (
    EvaluationRunIndex,
    EvaluatorExecution,
    EvaluatorInput,
)
from app.stt_benchmark.evaluators.contract import (
    Evaluator,
    EvaluatorFailure,
    EvaluatorSettings,
)
from app.stt_benchmark.evaluators.registry import EvaluatorRegistry
from app.stt_benchmark.storage.artifacts import EvaluationArtifactStore


class EvaluationOrchestrator:
    def __init__(
        self,
        registry: EvaluatorRegistry,
        settings: EvaluatorSettings,
        artifact_store: EvaluationArtifactStore,
    ) -> None:
        self._evaluators = registry.select(settings.enabled_evaluators)
        self._settings = settings
        self._artifact_store = artifact_store

    async def run(
        self,
        inputs: tuple[EvaluatorInput, ...],
        evaluation_run_id: str,
    ) -> EvaluationRunIndex:
        self._artifact_store.create()
        semaphore = asyncio.Semaphore(self._settings.max_concurrency)

        async def guarded(
            evaluator_input: EvaluatorInput,
            evaluator: Evaluator,
        ) -> EvaluatorExecution:
            async with semaphore:
                return await self._run_one(evaluator_input, evaluator, evaluation_run_id)

        tasks = [
            guarded(evaluator_input, evaluator)
            for evaluator_input in inputs
            for evaluator in self._evaluators
        ]
        executions = await asyncio.gather(*tasks)
        index = EvaluationRunIndex(
            evaluation_run_id=evaluation_run_id,
            created_at=datetime.now(UTC),
            max_concurrency=self._settings.max_concurrency,
            enabled_evaluators=self._settings.enabled_evaluators,
            executions=tuple(executions),
        )
        self._artifact_store.write_index(index)
        return index

    async def _run_one(
        self,
        evaluator_input: EvaluatorInput,
        evaluator: Evaluator,
        evaluation_run_id: str,
    ) -> EvaluatorExecution:
        started_at = datetime.now(UTC)
        try:
            support = evaluator.supports(evaluator_input)
        except Exception as error:
            return self._execution(
                evaluator_input=evaluator_input,
                evaluator=evaluator,
                evaluation_run_id=evaluation_run_id,
                started_at=started_at,
                status="failed",
                reason=f"evaluator_support_check_failed:{type(error).__name__}",
            )
        if not support.supported:
            return self._execution(
                evaluator_input=evaluator_input,
                evaluator=evaluator,
                evaluation_run_id=evaluation_run_id,
                started_at=started_at,
                status="unsupported",
                reason=support.reason or "unsupported_input",
            )
        try:
            output = await evaluator.evaluate(evaluator_input)
            path, digest = self._artifact_store.write_native_result(
                sample_id=evaluator_input.sample_id,
                evaluator_id=evaluator.evaluator_id,
                output=output,
            )
        except EvaluatorFailure as error:
            return self._execution(
                evaluator_input=evaluator_input,
                evaluator=evaluator,
                evaluation_run_id=evaluation_run_id,
                started_at=started_at,
                status="failed",
                reason=error.reason,
            )
        except Exception as error:
            return self._execution(
                evaluator_input=evaluator_input,
                evaluator=evaluator,
                evaluation_run_id=evaluation_run_id,
                started_at=started_at,
                status="failed",
                reason=f"unexpected_evaluator_error:{type(error).__name__}",
            )
        return self._execution(
            evaluator_input=evaluator_input,
            evaluator=evaluator,
            evaluation_run_id=evaluation_run_id,
            started_at=started_at,
            status="success",
            raw_result_path=path,
            raw_result_sha256=digest,
            raw_result_media_type=output.media_type,
        )

    @staticmethod
    def _execution(
        *,
        evaluator_input: EvaluatorInput,
        evaluator: Evaluator,
        evaluation_run_id: str,
        started_at: datetime,
        status: str,
        reason: str | None = None,
        raw_result_path: str | None = None,
        raw_result_sha256: str | None = None,
        raw_result_media_type: str | None = None,
    ) -> EvaluatorExecution:
        return EvaluatorExecution(
            experiment_id=evaluator_input.experiment_id,
            evaluation_run_id=evaluation_run_id,
            sample_id=evaluator_input.sample_id,
            prediction_id=evaluator_input.prediction_id,
            gold_version=evaluator_input.gold_version,
            gold_version_source=evaluator_input.gold_version_source,
            gold_convention_version=evaluator_input.gold_convention_version,
            gold_review_status=evaluator_input.gold_review_status,
            gold_sha256=evaluator_input.gold_sha256,
            prediction_version=evaluator_input.prediction_version,
            prediction_sha256=evaluator_input.prediction_sha256,
            evaluator_id=evaluator.evaluator_id,
            evaluator_version=evaluator.evaluator_version,
            normalization_profile=evaluator.normalization_profile,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            status=status,
            raw_result_path=raw_result_path,
            raw_result_sha256=raw_result_sha256,
            raw_result_media_type=raw_result_media_type,
            reason=reason,
        )
