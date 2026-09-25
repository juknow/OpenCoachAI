"""Coordinate existing STT scores without models, files or network access.

This migration preserves the legacy report. Injectable, versioned metric profiles
are a separate implementation step and are not silently enabled here.
"""

from collections.abc import Iterable
from math import ceil

from app.stt_benchmark.contracts.dataset import TranscriptionDataset, TranscriptionSample
from app.stt_benchmark.contracts.evaluation import (
    AggregateRetention,
    TranscriptionEvaluationReport,
    TranscriptionSampleScore,
)
from app.stt_benchmark.contracts.run import TranscriptionObservation, TranscriptionRun
from app.stt_benchmark.metrics.counts import RetentionBreakdown
from app.stt_benchmark.metrics.filler import filler_retention
from app.stt_benchmark.metrics.hallucination import non_speech_word_count
from app.stt_benchmark.metrics.repetition import adjacent_repetition_retention
from app.stt_benchmark.metrics.word_error import word_error_breakdown
from app.stt_benchmark.text.normalization import normalized_words


def evaluate_transcription_run(
    dataset: TranscriptionDataset,
    run: TranscriptionRun,
) -> TranscriptionEvaluationReport:
    _validate_run_matches_dataset(dataset, run)
    observations = {observation.sample_id: observation for observation in run.observations}
    sample_scores = [_score_sample(sample, observations[sample.id]) for sample in dataset.samples]

    speech_scores = [score for score in sample_scores if score.expected_behavior == "transcribe"]
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
            f"run sample ids do not match dataset: missing={missing_ids}, extra={extra_ids}"
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
        hallucinated_words = non_speech_word_count(transcript)
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
