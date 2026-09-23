import logging
from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError, RateLimitError

from app.config import Settings
from app.errors import ProviderResponseError
from app.providers.openai_provider import OpenAIEvaluationProvider, OpenAITranscriptionProvider
from app.schemas.evaluation import CompactEvaluationOutput
from tests.helpers import evaluation_output


class FakeTranscriptions:
    def __init__(self) -> None:
        self.kwargs = None
        self.duration_seconds = None
        self.logprobs = [
            SimpleNamespace(token="Um", logprob=-0.1),
            SimpleNamespace(token=", I", logprob=-0.7),
        ]

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if self.duration_seconds is not None:
            return SimpleNamespace(
                text="Um, unchanged text.",
                usage=SimpleNamespace(
                    type="duration",
                    seconds=self.duration_seconds,
                ),
                logprobs=self.logprobs,
            )
        return SimpleNamespace(
            text="Um, unchanged text.",
            usage=SimpleNamespace(
                type="tokens",
                input_tokens=7,
                output_tokens=4,
                total_tokens=11,
            ),
            logprobs=self.logprobs,
        )


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None
        self.calls = 0
        self.rate_limit_once = False
        self.incomplete = False
        self.prompt_cache_error_once = False
        self.unrelated_bad_request = False
        self.history = []

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        self.history.append(kwargs)
        self.calls += 1
        if self.rate_limit_once and self.calls == 1:
            request = httpx.Request("POST", "https://api.openai.com/v1/responses")
            response = httpx.Response(429, request=request)
            raise RateLimitError("rate limited", response=response, body=None)
        if self.prompt_cache_error_once and self.calls == 1:
            request = httpx.Request("POST", "https://api.openai.com/v1/responses")
            response = httpx.Response(400, request=request)
            raise BadRequestError(
                "Unsupported parameter: 'prompt_cache_options'.",
                response=response,
                body={
                    "code": "unsupported_parameter",
                    "type": "invalid_request_error",
                },
            )
        if self.unrelated_bad_request:
            request = httpx.Request("POST", "https://api.openai.com/v1/responses")
            response = httpx.Response(400, request=request)
            raise BadRequestError(
                "invalid schema",
                response=response,
                body={
                    "code": "invalid_request_error",
                    "param": "text.format.schema",
                    "type": "invalid_request_error",
                },
            )
        if self.incomplete:
            return SimpleNamespace(
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
                output_parsed=None,
                model="gpt-5.6-luna",
                usage=None,
            )
        return SimpleNamespace(
            status="completed",
            output_parsed=evaluation_output(),
            model="gpt-5.6-luna",
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=200,
                total_tokens=300,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=30,
                    cache_write_tokens=12,
                ),
                output_tokens_details=SimpleNamespace(reasoning_tokens=5),
            ),
        )


class FakeClient:
    def __init__(self) -> None:
        self.audio = SimpleNamespace(transcriptions=FakeTranscriptions())
        self.responses = FakeResponses()


@pytest.mark.asyncio
async def test_openai_role_providers_use_bounded_cost_parameters_and_usage() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="not-real",
        openai_prompt_cache_enabled=True,
    )
    client = FakeClient()
    transcription_provider = OpenAITranscriptionProvider(settings, client=client)
    evaluation_provider = OpenAIEvaluationProvider(settings, client=client)
    assert not hasattr(transcription_provider, "evaluate")
    assert not hasattr(evaluation_provider, "transcribe")

    transcription = await transcription_provider.transcribe(
        audio=b"audio",
        filename="answer.webm",
        mime_type="audio/webm",
        prompt="preserve",
    )
    assert transcription.text == "Um, unchanged text."
    assert transcription.usage is not None
    assert transcription.usage.total_tokens == 11
    assert transcription.audio_seconds is None
    assert [(item.token, item.logprob) for item in transcription.token_logprobs] == [
        ("Um", -0.1),
        (", I", -0.7),
    ]
    assert client.audio.transcriptions.kwargs["model"] == "gpt-4o-mini-transcribe"
    assert client.audio.transcriptions.kwargs["include"] == ["logprobs"]
    assert "store" not in client.audio.transcriptions.kwargs

    result = await evaluation_provider.evaluate(
        system_prompt="evaluate",
        user_payload={"transcript": "Um"},
        response_model=CompactEvaluationOutput,
        prompt_cache_key="opic:evaluation-v2:gpt-5.6-luna:v1:v1",
    )
    kwargs = client.responses.kwargs
    assert kwargs["model"] == "gpt-5.6-luna"
    assert kwargs["reasoning"] == {"effort": "none"}
    assert kwargs["store"] is False
    assert "verbosity" not in kwargs
    assert kwargs["max_output_tokens"] == 2_400
    assert kwargs["text_format"] is CompactEvaluationOutput
    assert kwargs["prompt_cache_key"] == "opic:evaluation-v2:gpt-5.6-luna:v1:v1"
    assert kwargs["prompt_cache_options"] == {"mode": "explicit", "ttl": "30m"}
    assert kwargs["input"][0]["content"] == [
        {
            "type": "input_text",
            "text": "evaluate",
            "prompt_cache_breakpoint": {"mode": "explicit"},
        }
    ]
    assert kwargs["input"][1]["content"] == '{"transcript":"Um"}'
    assert result.usage is not None
    assert result.usage.model_dump(by_alias=True) == {
        "inputTokens": 100,
        "outputTokens": 200,
        "cachedInputTokens": 30,
        "cacheWriteTokens": 12,
        "reasoningTokens": 5,
        "totalTokens": 300,
    }


@pytest.mark.asyncio
async def test_transcription_provider_preserves_duration_usage() -> None:
    settings = Settings(_env_file=None, openai_api_key="not-real")
    client = FakeClient()
    client.audio.transcriptions.duration_seconds = 12.75
    provider = OpenAITranscriptionProvider(settings, client=client)

    transcription = await provider.transcribe(
        audio=b"audio",
        filename="answer.webm",
        mime_type="audio/webm",
        prompt="preserve",
    )

    assert transcription.usage is None
    assert transcription.audio_seconds == 12.75


@pytest.mark.asyncio
async def test_transcription_logprobs_can_be_disabled_for_incompatible_models() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="not-real",
        openai_transcription_logprobs_enabled=False,
    )
    client = FakeClient()
    provider = OpenAITranscriptionProvider(settings, client=client)

    await provider.transcribe(
        audio=b"audio",
        filename="answer.webm",
        mime_type="audio/webm",
        prompt="preserve",
    )

    assert "include" not in client.audio.transcriptions.kwargs


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "language_field", "includes_logprobs"),
    [
        ("gpt-transcribe", "languages", False),
        ("gpt-4o-transcribe", "language", True),
        ("gpt-4o-mini-transcribe-2025-12-15", "language", True),
        ("whisper-1", "language", False),
    ],
)
async def test_transcription_request_matches_model_capabilities(
    model: str, language_field: str, includes_logprobs: bool
) -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="not-real",
        openai_transcription_model=model,
    )
    client = FakeClient()
    provider = OpenAITranscriptionProvider(settings, client=client)

    await provider.transcribe(
        audio=b"audio",
        filename="answer.webm",
        mime_type="audio/webm",
        prompt="preserve",
    )

    kwargs = client.audio.transcriptions.kwargs
    assert kwargs["model"] == model
    assert kwargs["prompt"] == "preserve"
    assert kwargs["file"] == ("answer.webm", b"audio", "audio/webm")
    if language_field == "languages":
        assert kwargs["extra_body"] == {"languages": ["en"]}
        assert "language" not in kwargs
    else:
        assert kwargs["language"] == "en"
        assert "extra_body" not in kwargs
    assert (kwargs.get("include") == ["logprobs"]) is includes_logprobs


@pytest.mark.asyncio
async def test_transcription_provider_ignores_invalid_logprob_items() -> None:
    settings = Settings(_env_file=None, openai_api_key="not-real")
    client = FakeClient()
    client.audio.transcriptions.logprobs = [
        SimpleNamespace(token=None, logprob=-0.1),
        SimpleNamespace(token="", logprob=-0.2),
        SimpleNamespace(token="invalid", logprob=float("nan")),
        SimpleNamespace(token="invalid", logprob=True),
        SimpleNamespace(token="valid", logprob=-1.25),
    ]
    provider = OpenAITranscriptionProvider(settings, client=client)

    transcription = await provider.transcribe(
        audio=b"audio",
        filename="answer.webm",
        mime_type="audio/webm",
        prompt="preserve",
    )

    assert [(item.token, item.logprob) for item in transcription.token_logprobs] == [
        ("valid", -1.25)
    ]


@pytest.mark.asyncio
async def test_prompt_cache_is_disabled_by_default_without_changing_payload_order() -> None:
    settings = Settings(_env_file=None, openai_api_key="not-real")
    assert settings.openai_prompt_cache_enabled is False
    client = FakeClient()
    provider = OpenAIEvaluationProvider(settings, client=client)

    await provider.evaluate(
        system_prompt="stable prefix",
        user_payload={"transcript": "dynamic suffix"},
        response_model=CompactEvaluationOutput,
        prompt_cache_key="safe-key",
    )

    kwargs = client.responses.kwargs
    assert kwargs["input"][0]["content"] == "stable prefix"
    assert "prompt_cache_key" not in kwargs
    assert "prompt_cache_options" not in kwargs


@pytest.mark.asyncio
async def test_prompt_cache_compatibility_error_retries_once_without_cache() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="not-real",
        openai_prompt_cache_enabled=True,
    )
    client = FakeClient()
    client.responses.prompt_cache_error_once = True
    provider = OpenAIEvaluationProvider(settings, client=client)

    result = await provider.evaluate(
        system_prompt="stable prefix",
        user_payload={"transcript": "dynamic suffix"},
        response_model=CompactEvaluationOutput,
        prompt_cache_key="safe-key",
    )

    assert result.output is not None
    assert client.responses.calls == 2
    assert "prompt_cache_options" in client.responses.history[0]
    assert "prompt_cache_options" not in client.responses.history[1]
    assert client.responses.history[1]["input"][0]["content"] == "stable prefix"


@pytest.mark.asyncio
async def test_unrelated_bad_request_is_not_retried_without_cache() -> None:
    settings = Settings(_env_file=None, openai_api_key="not-real")
    client = FakeClient()
    client.responses.unrelated_bad_request = True
    provider = OpenAIEvaluationProvider(settings, client=client)

    with pytest.raises(BadRequestError):
        await provider.evaluate(
            system_prompt="evaluate",
            user_payload={"transcript": "Um"},
            response_model=CompactEvaluationOutput,
            prompt_cache_key="safe-key",
        )

    assert client.responses.calls == 1


@pytest.mark.asyncio
async def test_rate_limit_is_retried_once_by_controlled_provider_policy() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="not-real",
        openai_rate_limit_retry_delay_seconds=0,
    )
    client = FakeClient()
    client.responses.rate_limit_once = True
    provider = OpenAIEvaluationProvider(settings, client=client)

    await provider.evaluate(
        system_prompt="evaluate",
        user_payload={"transcript": "Um"},
        response_model=CompactEvaluationOutput,
    )

    assert client.responses.calls == 2


@pytest.mark.asyncio
async def test_truncated_structured_output_is_rejected_without_retry() -> None:
    settings = Settings(_env_file=None, openai_api_key="not-real")
    client = FakeClient()
    client.responses.incomplete = True
    provider = OpenAIEvaluationProvider(settings, client=client)

    with pytest.raises(ProviderResponseError, match="EVALUATION_OUTPUT_TRUNCATED"):
        await provider.evaluate(
            system_prompt="evaluate",
            user_payload={"transcript": "Um"},
            response_model=CompactEvaluationOutput,
        )

    assert client.responses.calls == 1


@pytest.mark.asyncio
async def test_usage_log_never_contains_sensitive_payloads(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="private-api-key-value",
        app_environment="development",
        openai_usage_log_enabled=True,
    )
    client = FakeClient()
    provider = OpenAIEvaluationProvider(settings, client=client)
    secret_transcript = "private transcript content"

    with caplog.at_level(logging.INFO, logger="opic.usage"):
        await provider.evaluate(
            system_prompt="private system prompt",
            user_payload={"transcript": secret_transcript},
            response_model=CompactEvaluationOutput,
        )

    log_text = caplog.text
    assert "openai_usage" in log_text
    assert secret_transcript not in log_text
    assert "private system prompt" not in log_text
    assert "private-api-key-value" not in log_text
    assert "One of my favorite places" not in log_text
