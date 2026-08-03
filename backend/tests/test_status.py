import httpx
from fastapi.testclient import TestClient
from openai import BadRequestError, PermissionDeniedError, RateLimitError

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


def _client_with_status_error(error: Exception) -> TestClient:
    class FailingProvider:
        async def evaluate(self, **_kwargs):
            raise error

    app = create_app()
    app.dependency_overrides[get_ai_provider] = lambda: FailingProvider()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        openai_api_key="test-key-not-a-real-secret",
    )
    return TestClient(app, raise_server_exceptions=False)


def test_openai_invalid_request_returns_actionable_safe_error() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    error = BadRequestError(
        "raw provider detail must stay private",
        response=httpx.Response(400, request=request),
        body={
            "code": "invalid_request_error",
            "param": "text.format.schema",
            "type": "invalid_request_error",
        },
    )
    from tests.helpers import evaluation_request

    with _client_with_status_error(error) as client:
        response = client.post("/api/v2/evaluations", json=evaluation_request())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "OPENAI_INVALID_REQUEST"
    assert "raw provider detail" not in response.text


def test_openai_status_log_only_contains_safe_labels(caplog) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    error = BadRequestError(
        "private transcript and provider message",
        response=httpx.Response(400, request=request),
        body={
            "code": "invalid_request_error",
            "param": "text.format.schema",
            "type": "invalid_request_error",
        },
    )
    from tests.helpers import evaluation_request

    with (
        caplog.at_level("WARNING", logger="opic.openai"),
        _client_with_status_error(error) as client,
    ):
        response = client.post("/api/v2/evaluations", json=evaluation_request())

    assert response.status_code == 502
    assert "status=400" in caplog.text
    assert "code=invalid_request_error" in caplog.text
    assert "param=text.format.schema" in caplog.text
    assert "private transcript" not in caplog.text


def test_openai_status_log_safely_infers_known_missing_parameter(caplog) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    error = BadRequestError(
        "Unsupported parameter: 'prompt_cache_options'. private content",
        response=httpx.Response(400, request=request),
        body={"code": "unsupported_parameter", "type": "invalid_request_error"},
    )
    from tests.helpers import evaluation_request

    with (
        caplog.at_level("WARNING", logger="opic.openai"),
        _client_with_status_error(error) as client,
    ):
        response = client.post("/api/v2/evaluations", json=evaluation_request())

    assert response.status_code == 502
    assert "code=unsupported_parameter" in caplog.text
    assert "param=prompt_cache_options" in caplog.text
    assert "private content" not in caplog.text


def test_openai_model_permission_error_is_distinguished_safely() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    error = PermissionDeniedError(
        "private permission detail",
        response=httpx.Response(403, request=request),
        body={"code": "model_not_allowed", "type": "insufficient_permissions"},
    )
    from tests.helpers import evaluation_request

    with _client_with_status_error(error) as client:
        response = client.post("/api/v2/evaluations", json=evaluation_request())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "OPENAI_MODEL_UNAVAILABLE"
    assert "private permission detail" not in response.text


def test_openai_quota_error_is_distinguished_safely() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    error = RateLimitError(
        "private quota detail",
        response=httpx.Response(429, request=request),
        body={"code": "insufficient_quota", "type": "insufficient_quota"},
    )
    from tests.helpers import evaluation_request

    with _client_with_status_error(error) as client:
        response = client.post("/api/v2/evaluations", json=evaluation_request())

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "OPENAI_QUOTA_EXCEEDED"
    assert "private quota detail" not in response.text
