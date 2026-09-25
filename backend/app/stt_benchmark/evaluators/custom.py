import json

from app.stt_benchmark.contracts.dataset import TranscriptionDataset, TranscriptionSample
from app.stt_benchmark.contracts.evaluator import EvaluatorInput
from app.stt_benchmark.contracts.run import (
    TranscriptionObservation,
    TranscriptionRun,
    TranscriptionRunConfig,
)
from app.stt_benchmark.evaluation_engine import evaluate_transcription_run
from app.stt_benchmark.evaluators.contract import NativeEvaluatorOutput, SupportDecision


class CustomEvaluator:
    evaluator_id = "custom"
    evaluator_version = "legacy-v1"
    normalization_profile = "legacy-english-token-v1"
    required_inputs = frozenset({"gold_text", "prediction_text", "prediction_status"})
    supported_metrics = frozenset(
        {
            "word_error_rate",
            "filler_count_retention",
            "adjacent_repetition_count_retention",
            "non_speech_generated_words",
        }
    )

    def supports(self, evaluator_input: EvaluatorInput) -> SupportDecision:
        return SupportDecision.yes()

    async def evaluate(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        sample = TranscriptionSample(
            id=evaluator_input.sample_id,
            audio_path=f"samples/{evaluator_input.sample_id}.wav",
            reference_transcript=evaluator_input.gold_text,
            tags=["multi-engine-evaluation"],
            duration_seconds=evaluator_input.duration_seconds,
            language=evaluator_input.language,
            source="synthetic",
            expected_behavior=evaluator_input.expected_behavior,
        )
        observation = TranscriptionObservation(
            sample_id=evaluator_input.sample_id,
            status=evaluator_input.observed_status,
            transcript=evaluator_input.prediction_text,
            latency_ms=evaluator_input.latency_ms,
            error_code=evaluator_input.error_code,
        )
        dataset = TranscriptionDataset(
            version=evaluator_input.legacy_dataset_version,
            samples=[sample],
        )
        run = TranscriptionRun(
            experiment_id=evaluator_input.experiment_id,
            dataset_version=evaluator_input.legacy_dataset_version,
            model=evaluator_input.model,
            prompt_version=evaluator_input.prompt_version,
            created_at="2000-01-01T00:00:00Z",
            config=TranscriptionRunConfig(),
            observations=[observation],
        )
        report = evaluate_transcription_run(dataset, run)
        payload = json.dumps(
            report.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        return NativeEvaluatorOutput(payload=payload, suffix=".json", media_type="application/json")
