from fastapi.testclient import TestClient

from tests.conftest import FakeProvider
from tests.helpers import evaluation_request

WEBM = b"\x1aE\xdf\xa3" + b"0" * 1_024


def test_v3_transcription_returns_raw_text_and_deterministic_metrics(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    fake_provider.transcription_text = "Um, I I went there yesterday."
    response = client.post(
        "/api/v3/transcriptions",
        files={"audio": ("answer.webm", WEBM, "audio/webm")},
        data={"durationSeconds": "12", "attemptNumber": "1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["rawTranscript"] == fake_provider.transcription_text
    assert payload["speechMetrics"]["wordCount"] == 6
    assert payload["speechMetrics"]["fillerWords"] == [{"word": "um", "count": 1}]
    assert payload["model"] == "small.en"


def test_v3_evaluation_uses_confirmed_transcript_without_overwriting_raw(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    payload = evaluation_request()
    payload.pop("transcript")
    payload["rawTranscript"] = "Um, I goed to the park."
    payload["confirmedTranscript"] = "Um, I went to the park."

    response = client.post("/api/v3/evaluations", json=payload)

    assert response.status_code == 200
    assert fake_provider.evaluation_calls[0]["user_payload"]["transcript"] == payload[
        "confirmedTranscript"
    ]
    assert payload["rawTranscript"] != payload["confirmedTranscript"]
