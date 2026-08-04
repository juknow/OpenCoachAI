from fastapi.testclient import TestClient

from app.api.dependencies import get_ai_provider
from app.config import Settings, get_settings
from app.main import create_app
from app.providers.local_provider import FasterWhisperProvider, LocalAiProvider


def test_local_readiness_reports_models_without_loading_or_calling_them(monkeypatch) -> None:
    settings = Settings(_env_file=None, ai_provider="local")
    provider = LocalAiProvider(settings)

    async def ollama_ready() -> tuple[bool, bool, str]:
        return True, True, settings.ollama_model

    provider.evaluation.readiness = ollama_ready  # type: ignore[method-assign]
    monkeypatch.setattr(
        FasterWhisperProvider,
        "library_available",
        property(lambda _self: True),
    )
    monkeypatch.setattr(
        FasterWhisperProvider,
        "model_available",
        property(lambda _self: True),
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_ai_provider] = lambda: provider

    with TestClient(app) as client:
        response = client.get("/api/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "local",
        "ready": True,
        "ollama": {
            "running": True,
            "modelAvailable": True,
            "model": "qwen3:4b",
        },
        "whisper": {
            "libraryAvailable": True,
            "modelAvailable": True,
            "modelLoaded": False,
            "model": "base.en",
            "device": "cpu",
            "computeType": "int8",
        },
        "issues": [],
    }


def test_local_readiness_distinguishes_missing_ollama_model(monkeypatch) -> None:
    settings = Settings(_env_file=None, ai_provider="local")
    provider = LocalAiProvider(settings)

    async def model_missing() -> tuple[bool, bool, str]:
        return True, False, settings.ollama_model

    provider.evaluation.readiness = model_missing  # type: ignore[method-assign]
    monkeypatch.setattr(
        FasterWhisperProvider,
        "library_available",
        property(lambda _self: True),
    )
    monkeypatch.setattr(
        FasterWhisperProvider,
        "model_available",
        property(lambda _self: True),
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_ai_provider] = lambda: provider

    with TestClient(app) as client:
        payload = client.get("/api/readiness").json()

    assert payload["ready"] is False
    assert payload["issues"] == ["OLLAMA_MODEL_UNAVAILABLE"]
