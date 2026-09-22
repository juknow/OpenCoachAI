from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.evals.transcription_run import TranscriptionRun


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
