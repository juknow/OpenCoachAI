from types import SimpleNamespace

import pytest

from app.config import Settings
from app.providers.openai_provider import OpenAIProvider
from app.schemas.evaluation import EvaluationModelOutput
from tests.helpers import evaluation_output


class FakeTranscriptions:
    def __init__(self) -> None:
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(text="Um, unchanged text.")


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            output_parsed=evaluation_output(),
            model="gpt-5.6-luna",
            usage=SimpleNamespace(
                input_tokens=10,
                output_tokens=20,
                input_tokens_details=SimpleNamespace(cached_tokens=3),
            ),
        )


class FakeClient:
    def __init__(self) -> None:
        self.audio = SimpleNamespace(transcriptions=FakeTranscriptions())
        self.responses = FakeResponses()


@pytest.mark.asyncio
async def test_openai_provider_uses_required_models_and_parameters() -> None:
    settings = Settings(_env_file=None, openai_api_key="not-real")
    client = FakeClient()
    provider = OpenAIProvider(settings, client=client)

    transcription = await provider.transcribe(
        audio=b"audio",
        filename="answer.webm",
        mime_type="audio/webm",
        prompt="preserve",
    )
    assert transcription.text == "Um, unchanged text."
    assert client.audio.transcriptions.kwargs["model"] == "gpt-4o-mini-transcribe"
    assert "store" not in client.audio.transcriptions.kwargs

    result = await provider.evaluate(
        system_prompt="evaluate",
        user_payload={"transcript": "Um"},
        response_model=EvaluationModelOutput,
    )
    kwargs = client.responses.kwargs
    assert kwargs["model"] == "gpt-5.6-luna"
    assert kwargs["reasoning"] == {"effort": "none"}
    assert kwargs["store"] is False
    assert kwargs["text_format"] is EvaluationModelOutput
    assert result.usage.cached_input_tokens == 3
