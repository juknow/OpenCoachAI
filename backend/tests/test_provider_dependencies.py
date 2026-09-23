import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import dependencies
from app.api.dependencies import get_evaluation_provider, get_transcription_provider
from app.config import Settings, get_settings
from app.main import create_app
from app.providers.local_whisper_provider import LocalWhisperTranscriptionProvider
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


def test_local_whisper_can_be_selected_without_loading_model_early(monkeypatch) -> None:
    model_loads: list[str] = []

    class FakeWhisperModel:
        def transcribe(self, _audio, **_kwargs):
            return iter([SimpleNamespace(text=" Um, I I went there.")]), SimpleNamespace(
                duration=4.25
            )

    def load_model(model_name: str) -> FakeWhisperModel:
        model_loads.append(model_name)
        return FakeWhisperModel()

    monkeypatch.setattr(dependencies, "load_local_whisper_model", load_model)
    settings = Settings(
        _env_file=None,
        openai_api_key=None,
        transcription_provider="local_whisper",
        local_whisper_model="small.en",
    )
    provider = get_transcription_provider(settings)
    assert isinstance(provider, LocalWhisperTranscriptionProvider)
    assert model_loads == []

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app, raise_server_exceptions=False) as client:
        invalid = client.post(
            "/api/transcriptions",
            files={"audio": ("answer.webm", b"not-webm" + b"0" * 1_024, "audio/webm")},
            data={"durationSeconds": "12", "attemptNumber": "1"},
        )
        assert invalid.status_code == 415
        assert model_loads == []

        valid = client.post(
            "/api/transcriptions",
            files={"audio": ("answer.webm", WEBM, "audio/webm")},
            data={"durationSeconds": "12", "attemptNumber": "1"},
        )

    assert valid.status_code == 200
    assert valid.json()["transcript"] == " Um, I I went there."
    assert valid.json()["metadata"]["model"] == "local-whisper/small.en"
    assert valid.json()["metadata"]["usage"] is None
    assert model_loads == ["small.en"]


def test_local_whisper_model_load_failure_returns_safe_error(monkeypatch) -> None:
    def fail_to_load(_model_name: str):
        raise OSError("private model cache path")

    monkeypatch.setattr(dependencies, "_cached_local_whisper_model", fail_to_load)
    settings = Settings(_env_file=None, transcription_provider="local_whisper")
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/transcriptions",
            files={"audio": ("answer.webm", WEBM, "audio/webm")},
            data={"durationSeconds": "12", "attemptNumber": "1"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LOCAL_STT_UNAVAILABLE"
    assert "private model cache path" not in str(response.json())


def test_local_whisper_model_is_loaded_once_per_process(monkeypatch) -> None:
    created_models: list[object] = []

    class FakeWhisperModel:
        def __init__(self, model_name: str, *, device: str, compute_type: str) -> None:
            assert (model_name, device, compute_type) == ("small.en", "cpu", "int8")
            created_models.append(self)

    monkeypatch.setitem(
        sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeWhisperModel)
    )
    dependencies._cached_local_whisper_model.cache_clear()
    try:
        first = dependencies.load_local_whisper_model("small.en")
        second = dependencies.load_local_whisper_model("small.en")
        assert first is second
        assert created_models == [first]
    finally:
        dependencies._cached_local_whisper_model.cache_clear()


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
