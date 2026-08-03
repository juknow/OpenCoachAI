import json
from typing import Any, cast

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import Settings
from app.errors import ProviderResponseError
from app.providers.base import OutputModel, ProviderEvaluation, ProviderTranscription
from app.schemas.common import UsageMetadata


class OpenAIProvider:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        if not settings.openai_configured:
            raise ProviderResponseError("OPENAI_NOT_CONFIGURED")
        self._settings = settings
        self._client = client or AsyncOpenAI(
            api_key=cast(str, settings.openai_api_key.get_secret_value()),
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )

    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str,
        mime_type: str,
        prompt: str,
    ) -> ProviderTranscription:
        response = await self._client.audio.transcriptions.create(
            model=self._settings.openai_transcription_model,
            file=(filename, audio, mime_type),
            language="en",
            prompt=prompt,
        )
        text = getattr(response, "text", None)
        if not isinstance(text, str):
            raise ProviderResponseError("INVALID_TRANSCRIPTION_RESPONSE")
        return ProviderTranscription(text=text, model=self._settings.openai_transcription_model)

    async def evaluate(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, object],
        response_model: type[OutputModel],
    ) -> ProviderEvaluation:
        response = await self._client.responses.parse(
            model=self._settings.openai_evaluation_model,
            reasoning={"effort": "none"},
            store=False,
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":")),
                },
            ],
            text_format=response_model,
        )
        parsed = getattr(response, "output_parsed", None)
        if not isinstance(parsed, BaseModel):
            raise ProviderResponseError("INVALID_EVALUATION_RESPONSE")

        usage_value = getattr(response, "usage", None)
        usage = None
        if usage_value is not None:
            details = getattr(usage_value, "input_tokens_details", None)
            usage = UsageMetadata(
                input_tokens=max(0, int(getattr(usage_value, "input_tokens", 0) or 0)),
                output_tokens=max(0, int(getattr(usage_value, "output_tokens", 0) or 0)),
                cached_input_tokens=max(0, int(getattr(details, "cached_tokens", 0) or 0)),
            )

        return ProviderEvaluation(
            output=parsed,
            model=str(getattr(response, "model", self._settings.openai_evaluation_model)),
            usage=usage,
        )
