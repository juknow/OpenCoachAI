from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_ai_provider
from app.config import Settings, get_settings
from app.main import create_app
from app.providers.base import ProviderEvaluation, ProviderTranscription
from app.schemas.common import UsageMetadata
from app.schemas.evaluation import CompactEvaluationV2Output, CompactHigherAnswerOutput
from tests.helpers import evaluation_output, evaluation_v2_output, higher_answer_output


@dataclass
class FakeProvider:
    transcription_text: str = "Um, I I went there yesterday."
    transcription_calls: list[dict[str, object]] = field(default_factory=list)
    evaluation_calls: list[dict[str, object]] = field(default_factory=list)
    evaluation_error: Exception | None = None

    async def transcribe(self, **kwargs) -> ProviderTranscription:
        self.transcription_calls.append(kwargs)
        return ProviderTranscription(text=self.transcription_text, model="small.en")

    async def evaluate(self, **kwargs) -> ProviderEvaluation:
        self.evaluation_calls.append(kwargs)
        if self.evaluation_error:
            raise self.evaluation_error
        response_model = kwargs["response_model"]
        if response_model is CompactEvaluationV2Output:
            output = evaluation_v2_output()
        elif response_model is CompactHigherAnswerOutput:
            output = higher_answer_output()
        else:
            output = evaluation_output()
        return ProviderEvaluation(
            output=output,
            model="qwen3:8b",
            usage=UsageMetadata(
                input_tokens=120,
                output_tokens=340,
                cached_input_tokens=20,
                cache_write_tokens=10,
                reasoning_tokens=0,
                total_tokens=460,
            ),
        )


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def configured_settings() -> Settings:
    return Settings(
        _env_file=None,
        max_audio_bytes=900_000,
    )


@pytest.fixture
def client(fake_provider: FakeProvider, configured_settings: Settings) -> AsyncIterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_ai_provider] = lambda: fake_provider
    app.dependency_overrides[get_settings] = lambda: configured_settings
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
