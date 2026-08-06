from fastapi.testclient import TestClient

from app.api.dependencies import get_ai_provider
from app.config import Settings, get_settings
from app.errors import ProviderResponseError, ProviderUnavailableError
from app.main import create_app
from tests.helpers import evaluation_request


def test_health_does_not_call_models(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_legacy_openai_config_endpoint_is_removed(client: TestClient) -> None:
    assert client.get("/api/config/status").status_code == 404


def _client_with_provider_error(error: Exception) -> TestClient:
    class FailingProvider:
        async def evaluate(self, **_kwargs):
            raise error

    app = create_app()
    app.dependency_overrides[get_ai_provider] = lambda: FailingProvider()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    return TestClient(app, raise_server_exceptions=False)


def test_provider_error_does_not_expose_internal_message() -> None:
    error = ProviderResponseError("private transcript and internal model detail")
    with _client_with_provider_error(error) as client:
        response = client.post("/api/v3/evaluations", json=_v3_request())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "INVALID_AI_RESPONSE"
    assert "private transcript" not in response.text
    assert "Traceback" not in response.text


def test_truncated_model_response_has_actionable_error() -> None:
    with _client_with_provider_error(
        ProviderResponseError("EVALUATION_OUTPUT_TRUNCATED")
    ) as client:
        response = client.post("/api/v3/evaluations", json=_v3_request())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_OUTPUT_TRUNCATED"


def test_ollama_unavailable_is_distinguished_without_internal_details() -> None:
    with _client_with_provider_error(
        ProviderUnavailableError("OLLAMA_UNAVAILABLE")
    ) as client:
        response = client.post("/api/v3/evaluations", json=_v3_request())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OLLAMA_UNAVAILABLE"


def _v3_request() -> dict[str, object]:
    payload = evaluation_request()
    transcript = str(payload.pop("transcript"))
    payload["rawTranscript"] = transcript
    payload["confirmedTranscript"] = transcript
    return payload
