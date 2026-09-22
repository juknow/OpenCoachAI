from collections.abc import Iterable
from math import ceil
from typing import Literal

from pydantic import Field

from app.evals.transcription_dataset import TranscriptionDataset, TranscriptionSample
from app.evals.transcription_metrics import (
    RetentionBreakdown,
    adjacent_repetition_retention,
    filler_retention,
    normalized_words,
    word_error_breakdown,
)
from app.evals.transcription_run import TranscriptionObservation, TranscriptionRun
from app.schemas.common import ApiModel


class AggregateRetention(ApiModel):
    reference_items: int = Field(ge=0)
    hypothesis_items: int = Field(ge=0)
    matched_items: int = Field(ge=0)
    recall: float | None = Field(default=None, ge=0, le=1)
    precision: float | None = Field(default=None, ge=0, le=1)


class TranscriptionSampleScore(ApiModel):
    sample_id: str
    expected_behavior: Literal["transcribe", "empty-or-rejected", "rejected"]
    observed_status: Literal["transcribed", "rejected", "failed"]
    reference_words: int = Field(ge=0)
    hypothesis_words: int = Field(ge=0)
    word_errors: int = Field(ge=0)
    word_error_rate: float | None = Field(default=None, ge=0)
    filler: AggregateRetention
    repetition: AggregateRetention
    hallucinated_words: int = Field(ge=0)
    unexpected_outcome: bool
    latency_ms: int = Field(ge=0)
    error_code: str | None = None


class TranscriptionEvaluationReport(ApiModel):
    experiment_id: str
    dataset_version: str
    model: str
    prompt_version: str
    sample_count: int = Field(ge=1)
    speech_samples: int = Field(ge=0)
    failed_speech_samples: int = Field(ge=0)
    reference_words: int = Field(ge=0)
    word_errors: int = Field(ge=0)
    word_error_rate: float | None = Field(default=None, ge=0)
    filler: AggregateRetention
    repetition: AggregateRetention
    non_speech_samples: int = Field(ge=0)
    hallucination_samples: int = Field(ge=0)
    unexpected_outcome_samples: int = Field(ge=0)
    latency_p50_ms: int = Field(ge=0)
    latency_p95_ms: int = Field(ge=0)
    samples: list[TranscriptionSampleScore]


def evaluate_transcription_run(
    dataset: TranscriptionDataset,
    run: TranscriptionRun,
) -> TranscriptionEvaluationReport:
    _validate_run_matches_dataset(dataset, run)
    observations = {observation.sample_id: observation for observation in run.observations}
    sample_scores = [
        _score_sample(sample, observations[sample.id]) for sample in dataset.samples
    ]

    speech_scores = [
        score for score in sample_scores if score.expected_behavior == "transcribe"
    ]
    reference_words = sum(score.reference_words for score in speech_scores)
    word_errors = sum(score.word_errors for score in speech_scores)
    latencies = [score.latency_ms for score in sample_scores]

    return TranscriptionEvaluationReport(
        experiment_id=run.experiment_id,
        dataset_version=dataset.version,
        model=run.model,
        prompt_version=run.prompt_version,
        sample_count=len(sample_scores),
        speech_samples=len(speech_scores),
        failed_speech_samples=sum(
            score.observed_status != "transcribed" or score.hypothesis_words == 0
            for score in speech_scores
        ),
        reference_words=reference_words,
        word_errors=word_errors,
        word_error_rate=word_errors / reference_words if reference_words else None,
        filler=_aggregate_retention(score.filler for score in speech_scores),
        repetition=_aggregate_retention(score.repetition for score in speech_scores),
        non_speech_samples=len(sample_scores) - len(speech_scores),
        hallucination_samples=sum(score.hallucinated_words > 0 for score in sample_scores),
        unexpected_outcome_samples=sum(score.unexpected_outcome for score in sample_scores),
        latency_p50_ms=_nearest_rank_percentile(latencies, 50),
        latency_p95_ms=_nearest_rank_percentile(latencies, 95),
        samples=sample_scores,
    )


def _validate_run_matches_dataset(
    dataset: TranscriptionDataset,
    run: TranscriptionRun,
) -> None:
    if run.dataset_version != dataset.version:
        raise ValueError(
            f"run dataset version {run.dataset_version!r} does not match {dataset.version!r}"
        )

    dataset_ids = {sample.id for sample in dataset.samples}
    observation_ids = {observation.sample_id for observation in run.observations}
    missing_ids = sorted(dataset_ids - observation_ids)
    extra_ids = sorted(observation_ids - dataset_ids)
    if missing_ids or extra_ids:
        raise ValueError(
            "run sample ids do not match dataset: "
            f"missing={missing_ids}, extra={extra_ids}"
        )


def _score_sample(
    sample: TranscriptionSample,
    observation: TranscriptionObservation,
) -> TranscriptionSampleScore:
    transcript = observation.transcript if observation.status == "transcribed" else ""
    hypothesis_words = len(normalized_words(transcript))
    filler = filler_retention(sample.reference_transcript, transcript)
    repetition = adjacent_repetition_retention(sample.reference_transcript, transcript)

    if sample.expected_behavior == "transcribe":
        word_errors = word_error_breakdown(sample.reference_transcript, transcript)
        unexpected_outcome = observation.status != "transcribed" or hypothesis_words == 0
        hallucinated_words = 0
        word_error_rate: float | None = word_errors.word_error_rate
    else:
        word_errors = word_error_breakdown("", "")
        hallucinated_words = hypothesis_words
        if sample.expected_behavior == "empty-or-rejected":
            unexpected_outcome = observation.status == "failed" or hallucinated_words > 0
        else:
            unexpected_outcome = observation.status != "rejected"
        word_error_rate = None

    return TranscriptionSampleScore(
        sample_id=sample.id,
        expected_behavior=sample.expected_behavior,
        observed_status=observation.status,
        reference_words=word_errors.reference_words,
        hypothesis_words=hypothesis_words,
        word_errors=word_errors.errors,
        word_error_rate=word_error_rate,
        filler=_retention_model(filler),
        repetition=_retention_model(repetition),
        hallucinated_words=hallucinated_words,
        unexpected_outcome=unexpected_outcome,
        latency_ms=observation.latency_ms,
        error_code=observation.error_code,
    )


def _retention_model(value: RetentionBreakdown) -> AggregateRetention:
    return AggregateRetention(
        reference_items=value.reference_items,
        hypothesis_items=value.hypothesis_items,
        matched_items=value.matched_items,
        recall=value.recall,
        precision=value.precision,
    )


def _aggregate_retention(values: Iterable[AggregateRetention]) -> AggregateRetention:
    items = list(values)
    reference_items = sum(item.reference_items for item in items)
    hypothesis_items = sum(item.hypothesis_items for item in items)
    matched_items = sum(item.matched_items for item in items)
    return AggregateRetention(
        reference_items=reference_items,
        hypothesis_items=hypothesis_items,
        matched_items=matched_items,
        recall=matched_items / reference_items if reference_items else None,
        precision=matched_items / hypothesis_items if hypothesis_items else None,
    )


def _nearest_rank_percentile(values: list[int], percentile: int) -> int:
    ordered = sorted(values)
    index = max(0, ceil((percentile / 100) * len(ordered)) - 1)
    return ordered[index]
