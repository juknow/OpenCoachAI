import asyncio
import json
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any, cast

from openai import AsyncOpenAI, RateLimitError
from pydantic import BaseModel

from app.config import Settings
from app.errors import ProviderResponseError
from app.providers.base import OutputModel, ProviderEvaluation, ProviderTranscription
from app.schemas.common import UsageMetadata
from app.usage_telemetry import record_usage_event, usage_event


class OpenAIProvider:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        if not settings.openai_configured:
            raise ProviderResponseError("OPENAI_NOT_CONFIGURED")
        self._settings = settings
        self._client = client or AsyncOpenAI(
            api_key=cast(str, settings.openai_api_key.get_secret_value()),
            timeout=settings.openai_timeout_seconds,
            max_retries=0,
        )

    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str,
        mime_type: str,
        prompt: str,
    ) -> ProviderTranscription:
        model = self._settings.openai_transcription_model
        started = perf_counter()
        retry_count = 0
        try:
            response, retry_count = await self._with_rate_limit_retry(
                lambda: self._client.audio.transcriptions.create(
                    model=model,
                    file=(filename, audio, mime_type),
                    language="en",
                    prompt=prompt,
                )
            )
            text = getattr(response, "text", None)
            if not isinstance(text, str):
                raise ProviderResponseError("INVALID_TRANSCRIPTION_RESPONSE")
            usage, audio_seconds = self._transcription_usage(response)
            self._record(
                request_type="transcription",
                model=model,
                started=started,
                success=True,
                retry_count=retry_count,
                usage=usage,
                audio_seconds=audio_seconds,
            )
            return ProviderTranscription(text=text, model=model, usage=usage)
        except Exception as error:
            recorded_retries = (
                self._settings.openai_rate_limit_max_retries
                if isinstance(error, RateLimitError)
                else retry_count
            )
            self._record(
                request_type="transcription",
                model=model,
                started=started,
                success=False,
                retry_count=recorded_retries,
                error_type=type(error).__name__,
            )
            raise

    async def evaluate(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, object],
        response_model: type[OutputModel],
    ) -> ProviderEvaluation:
        model = self._settings.openai_evaluation_model
        started = perf_counter()
        retry_count = 0
        usage: UsageMetadata | None = None
        try:
            response, retry_count = await self._with_rate_limit_retry(
                lambda: self._client.responses.parse(
                    model=model,
                    reasoning={"effort": "none"},
                    store=False,
                    max_output_tokens=self._settings.openai_evaluation_max_output_tokens,
                    verbosity=self._settings.openai_evaluation_verbosity,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": json.dumps(
                                user_payload,
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                        },
                    ],
                    text_format=response_model,
                )
            )
            incomplete_reason = getattr(
                getattr(response, "incomplete_details", None),
                "reason",
                None,
            )
            usage = self._response_usage(response)
            if getattr(response, "status", None) == "incomplete":
                if incomplete_reason == "max_output_tokens":
                    raise ProviderResponseError("EVALUATION_OUTPUT_TRUNCATED")
                raise ProviderResponseError("INVALID_EVALUATION_RESPONSE")

            parsed = getattr(response, "output_parsed", None)
            if not isinstance(parsed, BaseModel):
                raise ProviderResponseError("INVALID_EVALUATION_RESPONSE")

            response_model_name = str(getattr(response, "model", model))
            self._record(
                request_type="evaluation",
                model=response_model_name,
                started=started,
                success=True,
                retry_count=retry_count,
                usage=usage,
            )
            return ProviderEvaluation(
                output=parsed,
                model=response_model_name,
                usage=usage,
            )
        except Exception as error:
            recorded_retries = (
                self._settings.openai_rate_limit_max_retries
                if isinstance(error, RateLimitError)
                else retry_count
            )
            self._record(
                request_type="evaluation",
                model=model,
                started=started,
                success=False,
                retry_count=recorded_retries,
                usage=usage,
                error_type=type(error).__name__,
            )
            raise

    async def _with_rate_limit_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
    ) -> tuple[Any, int]:
        retries = 0
        while True:
            try:
                return await operation(), retries
            except RateLimitError:
                if retries >= self._settings.openai_rate_limit_max_retries:
                    raise
                retries += 1
                if self._settings.openai_rate_limit_retry_delay_seconds:
                    await asyncio.sleep(self._settings.openai_rate_limit_retry_delay_seconds)

    @staticmethod
    def _response_usage(response: object) -> UsageMetadata | None:
        usage_value = getattr(response, "usage", None)
        if usage_value is None:
            return None
        input_details = getattr(usage_value, "input_tokens_details", None)
        output_details = getattr(usage_value, "output_tokens_details", None)
        input_tokens = max(0, int(getattr(usage_value, "input_tokens", 0) or 0))
        output_tokens = max(0, int(getattr(usage_value, "output_tokens", 0) or 0))
        return UsageMetadata(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=max(0, int(getattr(input_details, "cached_tokens", 0) or 0)),
            cache_write_tokens=max(
                0,
                int(getattr(input_details, "cache_write_tokens", 0) or 0),
            ),
            reasoning_tokens=max(
                0,
                int(getattr(output_details, "reasoning_tokens", 0) or 0),
            ),
            total_tokens=max(
                0,
                int(getattr(usage_value, "total_tokens", input_tokens + output_tokens) or 0),
            ),
        )

    @staticmethod
    def _transcription_usage(
        response: object,
    ) -> tuple[UsageMetadata | None, float | None]:
        usage_value = getattr(response, "usage", None)
        if usage_value is None:
            return None, None
        if getattr(usage_value, "type", None) == "duration":
            return None, max(0.0, float(getattr(usage_value, "seconds", 0) or 0))
        input_tokens = max(0, int(getattr(usage_value, "input_tokens", 0) or 0))
        output_tokens = max(0, int(getattr(usage_value, "output_tokens", 0) or 0))
        return (
            UsageMetadata(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=max(
                    0,
                    int(getattr(usage_value, "total_tokens", input_tokens + output_tokens) or 0),
                ),
            ),
            None,
        )

    def _record(
        self,
        *,
        request_type: str,
        model: str,
        started: float,
        success: bool,
        retry_count: int,
        usage: UsageMetadata | None = None,
        audio_seconds: float | None = None,
        error_type: str | None = None,
    ) -> None:
        record_usage_event(
            usage_event(
                request_type=request_type,
                model=model,
                latency_ms=round((perf_counter() - started) * 1_000),
                success=success,
                retry_count=retry_count,
                usage=usage,
                audio_seconds=audio_seconds,
                error_type=error_type,
            ),
            enabled=self._settings.detailed_usage_logging_enabled,
        )
