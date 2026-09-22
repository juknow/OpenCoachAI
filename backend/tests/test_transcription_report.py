from datetime import UTC, datetime

import pytest

from app.evals.transcription_dataset import TranscriptionDataset
from app.evals.transcription_report import evaluate_transcription_run
from app.evals.transcription_run import TranscriptionRun


def dataset() -> TranscriptionDataset:
    return TranscriptionDataset.model_validate(
        {
            "version": "stt-eval-v1",
            "samples": [
                {
                    "id": "speech-filler-001",
                    "audioPath": "samples/speech-filler-001.webm",
                    "referenceTranscript": "Um, I I went home.",
                    "tags": ["filler", "repetition"],
                    "durationSeconds": 3.0,
                    "source": "synthetic",
                    "expectedBehavior": "transcribe",
                },
                {
                    "id": "speech-failed-001",
                    "audioPath": "samples/speech-failed-001.webm",
                    "referenceTranscript": "I like parks.",
                    "tags": ["clean"],
                    "durationSeconds": 2.0,
                    "source": "synthetic",
                    "expectedBehavior": "transcribe",
                },
                {
                    "id": "silence-001",
                    "audioPath": "samples/silence-001.wav",
                    "referenceTranscript": "",
                    "tags": ["silence"],
                    "durationSeconds": 4.0,
                    "source": "synthetic",
                    "expectedBehavior": "empty-or-rejected",
                },
                {
                    "id": "corrupt-001",
                    "audioPath": "samples/corrupt-001.webm",
                    "referenceTranscript": "",
                    "tags": ["corrupt"],
                    "durationSeconds": 0,
                    "source": "synthetic",
                    "expectedBehavior": "rejected",
                },
            ],
        }
    )


def run() -> TranscriptionRun:
    return TranscriptionRun.model_validate(
        {
            "experimentId": "mini-prompt-v1",
            "datasetVersion": "stt-eval-v1",
            "model": "gpt-4o-mini-transcribe-2025-12-15",
            "promptVersion": "transcription-v1",
            "createdAt": datetime(2026, 9, 22, tzinfo=UTC).isoformat(),
            "config": {"language": "en", "chunking": "none"},
            "observations": [
                {
                    "sampleId": "speech-filler-001",
                    "status": "transcribed",
                    "transcript": "Um, I went home.",
                    "latencyMs": 100,
                },
                {
                    "sampleId": "speech-failed-001",
                    "status": "failed",
                    "latencyMs": 200,
                    "errorCode": "OPENAI_TIMEOUT",
                },
                {
                    "sampleId": "silence-001",
                    "status": "transcribed",
                    "transcript": "Hello there.",
                    "latencyMs": 300,
                },
                {
                    "sampleId": "corrupt-001",
                    "status": "rejected",
                    "latencyMs": 400,
                    "errorCode": "INVALID_AUDIO_FILE",
                },
            ],
        }
    )


def test_report_aggregates_accuracy_retention_hallucination_and_latency() -> None:
    report = evaluate_transcription_run(dataset(), run())

    assert report.sample_count == 4
    assert report.speech_samples == 2
    assert report.failed_speech_samples == 1
    assert report.reference_words == 8
    assert report.word_errors == 4
    assert report.word_error_rate == pytest.approx(0.5)
    assert report.filler.recall == pytest.approx(1.0)
    assert report.filler.precision == pytest.approx(1.0)
    assert report.repetition.recall == pytest.approx(0.0)
    assert report.repetition.precision is None
    assert report.non_speech_samples == 2
    assert report.hallucination_samples == 1
    assert report.unexpected_outcome_samples == 2
    assert report.latency_p50_ms == 200
    assert report.latency_p95_ms == 400


def test_failed_speech_is_scored_as_deleted_words() -> None:
    report = evaluate_transcription_run(dataset(), run())
    score = next(item for item in report.samples if item.sample_id == "speech-failed-001")

    assert score.reference_words == 3
    assert score.hypothesis_words == 0
    assert score.word_errors == 3
    assert score.word_error_rate == pytest.approx(1.0)
    assert score.unexpected_outcome is True


def test_non_speech_words_are_reported_as_hallucination() -> None:
    report = evaluate_transcription_run(dataset(), run())
    score = next(item for item in report.samples if item.sample_id == "silence-001")

    assert score.word_error_rate is None
    assert score.hallucinated_words == 2
    assert score.unexpected_outcome is True


def test_run_dataset_version_must_match() -> None:
    incompatible_run = run().model_copy(update={"dataset_version": "stt-eval-v2"})

    with pytest.raises(ValueError, match="does not match"):
        evaluate_transcription_run(dataset(), incompatible_run)


def test_run_must_contain_exactly_the_dataset_sample_ids() -> None:
    incomplete_run = run().model_copy(update={"observations": run().observations[:-1]})

    with pytest.raises(ValueError, match="missing=.*corrupt-001"):
        evaluate_transcription_run(dataset(), incomplete_run)
