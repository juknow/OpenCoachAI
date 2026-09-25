import hashlib
import json

from app.stt_benchmark.contracts.dataset import TranscriptionDataset
from app.stt_benchmark.contracts.evaluator import (
    EvaluationSupplement,
    EvaluationSupplements,
    EvaluatorInput,
)
from app.stt_benchmark.contracts.run import TranscriptionRun


def _prediction_id(run: TranscriptionRun, sample_id: str, transcript: str, status: str) -> str:
    identity = {
        "experiment_id": run.experiment_id,
        "sample_id": sample_id,
        "created_at": run.created_at.isoformat(),
        "model": run.model,
        "prompt_version": run.prompt_version,
        "status": status,
        "transcript": transcript,
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"prediction-{hashlib.sha256(encoded).hexdigest()}"


def build_evaluator_inputs(
    dataset: TranscriptionDataset,
    run: TranscriptionRun,
    supplements: EvaluationSupplements | None = None,
) -> tuple[EvaluatorInput, ...]:
    if run.dataset_version != dataset.version:
        raise ValueError("run dataset version does not match the manifest")

    samples = {sample.id: sample for sample in dataset.samples}
    observations = {observation.sample_id: observation for observation in run.observations}
    if samples.keys() != observations.keys():
        missing = sorted(samples.keys() - observations.keys())
        extra = sorted(observations.keys() - samples.keys())
        raise ValueError(f"run sample ids do not match dataset: missing={missing}, extra={extra}")

    supplement_by_id: dict[str, EvaluationSupplement] = {}
    if supplements:
        supplement_by_id = {item.sample_id: item for item in supplements.samples}
        unknown = sorted(supplement_by_id.keys() - samples.keys())
        if unknown:
            raise ValueError(f"supplements contain unknown sample ids: {unknown}")

    prediction_version = f"{run.experiment_id}@{run.created_at.isoformat()}"
    inputs: list[EvaluatorInput] = []
    for sample in dataset.samples:
        observation = observations[sample.id]
        supplement = supplement_by_id.get(sample.id)
        inputs.append(
            EvaluatorInput(
                experiment_id=run.experiment_id,
                sample_id=sample.id,
                prediction_id=(
                    supplement.prediction_id
                    if supplement and supplement.prediction_id
                    else _prediction_id(
                        run,
                        sample.id,
                        observation.transcript,
                        observation.status,
                    )
                ),
                gold_version=(
                    supplement.gold_version
                    if supplement and supplement.gold_version
                    else dataset.version
                ),
                prediction_version=(
                    supplement.prediction_version
                    if supplement and supplement.prediction_version
                    else prediction_version
                ),
                gold_text=sample.reference_transcript,
                prediction_text=observation.transcript,
                expected_behavior=sample.expected_behavior,
                observed_status=observation.status,
                language=sample.language,
                duration_seconds=sample.duration_seconds,
                latency_ms=observation.latency_ms,
                error_code=observation.error_code,
                model=run.model,
                prompt_version=run.prompt_version,
                legacy_dataset_version=dataset.version,
                gold_intended_text=(supplement.gold_intended_text if supplement else None),
                prediction_intended_text=(
                    supplement.prediction_intended_text if supplement else None
                ),
                reference_segments=(supplement.reference_segments if supplement else None),
                prediction_segments=(supplement.prediction_segments if supplement else None),
            )
        )
    return tuple(inputs)
