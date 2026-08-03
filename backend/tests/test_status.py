from fastapi.testclient import TestClient

from app.api.dependencies import get_ai_provider
from app.config import Settings, get_settings
from app.errors import ProviderResponseError
from app.main import create_app


def test_health_does_not_call_openai(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_config_status_only_returns_boolean() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        openai_api_key="private-test-value",
    )
    with TestClient(app) as client:
        payload = client.get("/api/config/status").json()
    assert payload == {"openaiConfigured": True}
    assert "private-test-value" not in str(payload)


def test_config_status_false_without_key() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        openai_api_key=None,
    )
    with TestClient(app) as client:
        assert client.get("/api/config/status").json() == {"openaiConfigured": False}


def test_process_environment_api_key_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-read-from-process-env")
    settings = Settings(_env_file=None)
    assert settings.openai_configured is False


def test_provider_error_does_not_expose_internal_message() -> None:
    class FailingProvider:
        async def evaluate(self, **_kwargs):
            raise ProviderResponseError("upstream detail sk-never-return-this")

    app = create_app()
    app.dependency_overrides[get_ai_provider] = lambda: FailingProvider()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        openai_api_key="test-key-not-a-real-secret",
    )
    from tests.helpers import evaluation_request

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/evaluations", json=evaluation_request())

    assert response.status_code == 502
    body = response.text
    assert "INVALID_AI_RESPONSE" in body
    assert "sk-never-return-this" not in body
    assert "Traceback" not in body
