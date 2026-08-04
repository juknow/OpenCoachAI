import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.config import Settings
from app.errors import ProviderResponseError
from app.providers.local_provider import FasterWhisperProvider, OllamaProvider
from app.schemas.evaluation import CompactHigherAnswerOutput
from tests.helpers import higher_answer_output


@pytest.mark.asyncio
async def test_ollama_provider_uses_structured_non_thinking_request(caplog) -> None:
    fixture = higher_answer_output()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3:4b"
        assert payload["think"] is False
        assert payload["stream"] is False
        assert payload["options"] == {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 900,
        }
        assert payload["format"]["type"] == "object"
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {"content": fixture.model_dump_json(by_alias=True)},
                "done": True,
                "prompt_eval_count": 321,
                "eval_count": 456,
            },
        )

    settings = Settings(
        _env_file=None,
        ai_provider="local",
        app_environment="development",
        usage_log_enabled=True,
    )
    provider = OllamaProvider(settings, transport=httpx.MockTransport(handler))
    with caplog.at_level("INFO", logger="opic.usage"):
        result = await provider.evaluate(
            system_prompt="Return the schema.",
            user_payload={"confirmedTranscript": "private learner transcript"},
            response_model=CompactHigherAnswerOutput,
            request_type="higher_answer",
            max_output_tokens=900,
        )

    assert result.output == fixture
    assert result.usage is not None
    assert result.usage.total_tokens == 777
    assert "ai_usage" in caplog.text
    assert "private learner transcript" not in caplog.text
    assert '"input_tokens":321' in caplog.text


@pytest.mark.asyncio
async def test_ollama_provider_rejects_truncated_structured_output() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {"content": '{"sentences": ['},
                "done_reason": "length",
            },
        )
    )
    provider = OllamaProvider(Settings(_env_file=None), transport=transport)
    with pytest.raises(ProviderResponseError, match="EVALUATION_OUTPUT_TRUNCATED"):
        await provider.evaluate(
            system_prompt="prompt",
            user_payload={},
            response_model=CompactHigherAnswerOutput,
        )


@pytest.mark.asyncio
async def test_faster_whisper_preserves_text_and_removes_temporary_file() -> None:
    verbatim_text = (
        " Um, I go, I went to, I went to the park yesterday and, uh, "
        "I meet my friend, but we, we couldn't play for a long time."
    )

    class FakeModel:
        path: str | None = None

        def transcribe(self, path: str, **kwargs):
            self.path = path
            assert Path(path).exists()
            assert kwargs["language"] == "en"
            assert kwargs["task"] == "transcribe"
            assert kwargs["word_timestamps"] is True
            assert kwargs["condition_on_previous_text"] is False
            assert kwargs["vad_filter"] is True
            assert kwargs["vad_parameters"] == {
                "threshold": 0.35,
                "min_speech_duration_ms": 0,
                "min_silence_duration_ms": 1000,
                "speech_pad_ms": 500,
            }
            words = [
                SimpleNamespace(word=" Um", start=0.4, end=0.7, probability=0.9),
                SimpleNamespace(word=" I", start=0.8, end=0.9, probability=0.95),
            ]
            segment = SimpleNamespace(text=verbatim_text, start=0.4, end=8.6, words=words)
            return iter([segment]), SimpleNamespace(language="en")

    fake_model = FakeModel()
    provider = FasterWhisperProvider(Settings(_env_file=None))
    provider._model = fake_model
    result = await provider.transcribe(
        audio=b"not-decoded-by-the-fake",
        filename="answer.webm",
        mime_type="audio/webm",
        prompt="verbatim",
    )

    assert result.text == verbatim_text.strip()
    assert "I go, I went to, I went to" in result.text
    assert "I meet" in result.text
    assert "we, we" in result.text
    assert [word.text for word in result.words] == [" Um", " I"]
    assert fake_model.path is not None
    assert not Path(fake_model.path).exists()
