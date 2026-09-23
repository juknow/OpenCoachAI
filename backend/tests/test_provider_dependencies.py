from fastapi.testclient import TestClient

from app.api.dependencies import get_evaluation_provider, get_transcription_provider
from app.config import Settings, get_settings
from app.main import create_app
from app.providers.openai_provider import OpenAIEvaluationProvider, OpenAITranscriptionProvider
from tests.conftest import FakeProvider
from tests.helpers import evaluation_request

WEBM = b"\x1aE\xdf\xa3" + b"0" * 1_024


def test_default_provider_factories_return_role_specific_adapters(
    configured_settings: Settings,
) -> None:
    transcription_provider = get_transcription_provider(configured_settings)
    evaluation_provider = get_evaluation_provider(configured_settings)

    assert isinstance(transcription_provider, OpenAITranscriptionProvider)
    assert isinstance(evaluation_provider, OpenAIEvaluationProvider)
    assert not hasattr(transcription_provider, "evaluate")
    assert not hasattr(evaluation_provider, "transcribe")


def test_transcription_and_evaluation_use_separate_provider_dependencies(
    configured_settings: Settings,
) -> None:
    transcription_provider = FakeProvider()
    evaluation_provider = FakeProvider()
    app = create_app()
    app.dependency_overrides[get_transcription_provider] = lambda: transcription_provider
    app.dependency_overrides[get_evaluation_provider] = lambda: evaluation_provider
    app.dependency_overrides[get_settings] = lambda: configured_settings

    with TestClient(app, raise_server_exceptions=False) as client:
        transcription = client.post(
            "/api/transcriptions",
            files={"audio": ("answer.webm", WEBM, "audio/webm")},
            data={"durationSeconds": "12", "attemptNumber": "1"},
        )
        evaluation = client.post("/api/evaluations", json=evaluation_request())

    assert transcription.status_code == 200
    assert evaluation.status_code == 200
    assert len(transcription_provider.transcription_calls) == 1
    assert not transcription_provider.evaluation_calls
    assert len(evaluation_provider.evaluation_calls) == 1
    assert not evaluation_provider.transcription_calls
