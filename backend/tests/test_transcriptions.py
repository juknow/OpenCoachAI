from fastapi.testclient import TestClient

from tests.conftest import FakeProvider

WEBM = b"\x1aE\xdf\xa3" + b"0" * 1_024


def test_transcription_preserves_provider_text(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    fake_provider.transcription_text = "  Um, I I went there yesterday.  "
    response = client.post(
        "/api/transcriptions",
        files={"audio": ("answer.webm", WEBM, "audio/webm;codecs=opus")},
        data={"durationSeconds": "12.5", "attemptNumber": "1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"] == fake_provider.transcription_text
    assert payload["requestId"]
    call = fake_provider.transcription_calls[0]
    assert call["mime_type"] == "audio/webm"
    assert "Preserve every audible filler" in str(call["prompt"])


def test_transcription_rejects_unsupported_mime(client: TestClient) -> None:
    response = client.post(
        "/api/transcriptions",
        files={"audio": ("answer.ogg", b"OggS" + b"0" * 1_024, "audio/ogg")},
        data={"durationSeconds": "12", "attemptNumber": "1"},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_AUDIO_TYPE"


def test_transcription_rejects_mismatched_signature(client: TestClient) -> None:
    response = client.post(
        "/api/transcriptions",
        files={"audio": ("answer.webm", b"not-webm" + b"0" * 1_024, "audio/webm")},
        data={"durationSeconds": "12", "attemptNumber": "1"},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "INVALID_AUDIO_FILE"


def test_transcription_accepts_short_audible_duration(client: TestClient) -> None:
    response = client.post(
        "/api/transcriptions",
        files={"audio": ("answer.webm", WEBM, "audio/webm")},
        data={"durationSeconds": "3", "attemptNumber": "1"},
    )
    assert response.status_code == 200


def test_transcription_rejects_zero_duration(client: TestClient) -> None:
    response = client.post(
        "/api/transcriptions",
        files={"audio": ("answer.webm", WEBM, "audio/webm")},
        data={"durationSeconds": "0", "attemptNumber": "1"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_AUDIO_DURATION"


def test_transcription_rejects_file_over_size_limit(client: TestClient) -> None:
    oversized_webm = b"\x1aE\xdf\xa3" + b"0" * 900_000
    response = client.post(
        "/api/transcriptions",
        files={"audio": ("answer.webm", oversized_webm, "audio/webm")},
        data={"durationSeconds": "12", "attemptNumber": "1"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "AUDIO_TOO_LARGE"
