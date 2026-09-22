from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evals.transcription_dataset import TranscriptionDataset

BACKEND_DIR = Path(__file__).resolve().parents[1]


def sample_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "clean-filler-001",
        "audioPath": "samples/clean-filler-001.webm",
        "referenceTranscript": "Um, I I usually go there on weekends.",
        "tags": ["clean", "filler", "repetition"],
        "durationSeconds": 5.8,
        "language": "en",
        "source": "synthetic",
        "expectedBehavior": "transcribe",
    }
    payload.update(overrides)
    return payload


def test_dataset_accepts_documented_camel_case_manifest() -> None:
    dataset = TranscriptionDataset.model_validate(
        {
            "version": "stt-eval-v1",
            "samples": [sample_payload()],
        }
    )

    assert dataset.samples[0].audio_path == "samples/clean-filler-001.webm"
    assert dataset.samples[0].reference_transcript.startswith("Um")


def test_example_manifest_matches_dataset_contract() -> None:
    manifest_path = BACKEND_DIR / "evals" / "transcription" / "manifest.example.json"

    dataset = TranscriptionDataset.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )

    assert len(dataset.samples) == 3
    assert {sample.expected_behavior for sample in dataset.samples} == {
        "transcribe",
        "empty-or-rejected",
        "rejected",
    }


@pytest.mark.parametrize(
    "audio_path",
    [
        "../private.webm",
        "/samples/absolute.webm",
        "recordings/outside.webm",
        "samples/not-audio.txt",
    ],
)
def test_dataset_rejects_unsafe_or_unsupported_audio_paths(audio_path: str) -> None:
    with pytest.raises(ValidationError):
        TranscriptionDataset.model_validate(
            {
                "version": "stt-eval-v1",
                "samples": [sample_payload(audioPath=audio_path)],
            }
        )


def test_transcribe_sample_requires_a_human_reference() -> None:
    with pytest.raises(ValidationError, match="reference transcript"):
        TranscriptionDataset.model_validate(
            {
                "version": "stt-eval-v1",
                "samples": [sample_payload(referenceTranscript="   ")],
            }
        )


def test_non_speech_sample_can_have_an_empty_reference() -> None:
    dataset = TranscriptionDataset.model_validate(
        {
            "version": "stt-eval-v1",
            "samples": [
                sample_payload(
                    id="silence-001",
                    audioPath="samples/silence-001.wav",
                    referenceTranscript="",
                    tags=["silence"],
                    source="public-license",
                    expectedBehavior="empty-or-rejected",
                )
            ],
        }
    )

    assert dataset.samples[0].reference_transcript == ""


def test_dataset_rejects_duplicate_sample_ids() -> None:
    with pytest.raises(ValidationError, match="sample ids must be unique"):
        TranscriptionDataset.model_validate(
            {
                "version": "stt-eval-v1",
                "samples": [sample_payload(), sample_payload(audioPath="samples/second.webm")],
            }
        )


@pytest.mark.parametrize(
    "tags",
    [
        ["clean", "clean"],
        ["MixedCase"],
        ["has spaces"],
    ],
)
def test_dataset_rejects_duplicate_or_unnormalized_tags(tags: list[str]) -> None:
    with pytest.raises(ValidationError):
        TranscriptionDataset.model_validate(
            {
                "version": "stt-eval-v1",
                "samples": [sample_payload(tags=tags)],
            }
        )


def test_dataset_rejects_unknown_manifest_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        TranscriptionDataset.model_validate(
            {
                "version": "stt-eval-v1",
                "samples": [sample_payload(secretNote="do not accept")],
            }
        )
