from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evals.transcription_run import TranscriptionRun

BACKEND_DIR = Path(__file__).resolve().parents[1]


def observation_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "sampleId": "clean-filler-001",
        "status": "transcribed",
        "transcript": "Um, I I usually go there on weekends.",
        "latencyMs": 840,
        "errorCode": None,
    }
    payload.update(overrides)
    return payload


def run_payload(*observations: dict[str, object]) -> dict[str, object]:
    return {
        "experimentId": "mini-prompt-v1",
        "datasetVersion": "stt-eval-v1",
        "model": "gpt-4o-mini-transcribe-2025-12-15",
        "promptVersion": "transcription-v1",
        "createdAt": datetime(2026, 9, 22, tzinfo=UTC).isoformat(),
        "config": {
            "language": "en",
            "chunking": "none",
            "temperature": None,
            "includeLogprobs": False,
        },
        "observations": list(observations) or [observation_payload()],
    }


def test_run_accepts_reproducible_model_prompt_and_config_metadata() -> None:
    run = TranscriptionRun.model_validate(run_payload())

    assert run.dataset_version == "stt-eval-v1"
    assert run.config.language == "en"
    assert run.config.chunking == "none"
    assert run.observations[0].latency_ms == 840


def test_example_run_matches_result_contract() -> None:
    run_path = BACKEND_DIR / "evals" / "transcription" / "run.example.json"

    run = TranscriptionRun.model_validate_json(run_path.read_text(encoding="utf-8"))

    assert run.dataset_version == "stt-eval-v1"
    assert len(run.observations) == 3
    assert run.config.prompt_sha256 is None
    assert run.observations[0].usage is None


def test_run_accepts_live_execution_metadata_and_serializes_camel_case() -> None:
    payload = run_payload(
        observation_payload(
            usage={"inputTokens": 7, "outputTokens": 4, "totalTokens": 11},
            audioSeconds=5.8,
        )
    )
    payload["config"] = {
        "language": "en",
        "chunking": "none",
        "promptSha256": "a" * 64,
        "timeoutSeconds": 60,
        "maxRetries": 1,
        "maxAudioBytes": 900_000,
    }

    run = TranscriptionRun.model_validate(payload)
    serialized = run.model_dump(by_alias=True)

    assert serialized["config"]["promptSha256"] == "a" * 64
    assert serialized["config"]["timeoutSeconds"] == 60
    assert serialized["config"]["maxRetries"] == 1
    assert serialized["config"]["maxAudioBytes"] == 900_000
    assert serialized["observations"][0]["usage"]["totalTokens"] == 11
    assert serialized["observations"][0]["audioSeconds"] == 5.8


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("promptSha256", "not-a-sha256"),
        ("timeoutSeconds", 0),
        ("maxRetries", -1),
        ("maxAudioBytes", 0),
    ],
)
def test_run_rejects_invalid_live_config_metadata(field: str, value: object) -> None:
    payload = run_payload()
    payload["config"][field] = value

    with pytest.raises(ValidationError):
        TranscriptionRun.model_validate(payload)


def test_run_rejects_negative_provider_audio_duration() -> None:
    with pytest.raises(ValidationError):
        TranscriptionRun.model_validate(
            run_payload(observation_payload(audioSeconds=-0.1))
        )


def test_run_rejects_duplicate_observation_ids() -> None:
    with pytest.raises(ValidationError, match="observation sample ids must be unique"):
        TranscriptionRun.model_validate(
            run_payload(
                observation_payload(),
                observation_payload(latencyMs=900),
            )
        )


def test_transcribed_observation_cannot_include_an_error_code() -> None:
    with pytest.raises(ValidationError, match="cannot have an error code"):
        TranscriptionRun.model_validate(
            run_payload(observation_payload(errorCode="OPENAI_TIMEOUT"))
        )


@pytest.mark.parametrize("status", ["rejected", "failed"])
def test_unsuccessful_observation_requires_an_error_code(status: str) -> None:
    with pytest.raises(ValidationError, match="require an error code"):
        TranscriptionRun.model_validate(
            run_payload(
                observation_payload(
                    status=status,
                    transcript="",
                    errorCode=None,
                )
            )
        )


def test_unsuccessful_observation_cannot_include_a_transcript() -> None:
    with pytest.raises(ValidationError, match="cannot have a transcript"):
        TranscriptionRun.model_validate(
            run_payload(
                observation_payload(
                    status="rejected",
                    transcript="invented text",
                    errorCode="INVALID_AUDIO_FILE",
                )
            )
        )


def test_run_rejects_unknown_fields() -> None:
    payload = run_payload()
    payload["privateTranscript"] = "must not be accepted"

    with pytest.raises(ValidationError, match="extra_forbidden"):
        TranscriptionRun.model_validate(payload)
