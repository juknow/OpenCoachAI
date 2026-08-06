import asyncio
import importlib.util
import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.errors import ProviderResponseError, ProviderUnavailableError
from app.providers.base import (
    EvaluationProvider,
    OutputModel,
    ProviderEvaluation,
    ProviderSegment,
    ProviderTranscription,
    ProviderWord,
    TranscriptionProvider,
)
from app.schemas.common import UsageMetadata
from app.usage_telemetry import record_usage_event, usage_event


class FasterWhisperProvider(TranscriptionProvider):
    """Lazy, process-wide faster-whisper adapter with no implicit model download."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: Any | None = None
        self._model_lock = asyncio.Lock()

    async def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        async with self._model_lock:
            if self._model is not None:
                return self._model
            self._model = await asyncio.to_thread(self._load_model)
        return self._model

    def _load_model(self) -> Any:
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise ProviderUnavailableError("WHISPER_NOT_INSTALLED") from error
        try:
            return WhisperModel(
                self._settings.whisper_model,
                device=self._settings.whisper_device,
                compute_type=self._settings.whisper_compute_type,
                cpu_threads=self._settings.whisper_cpu_threads,
                local_files_only=self._settings.whisper_local_files_only,
            )
        except Exception as error:
            raise ProviderUnavailableError("WHISPER_MODEL_UNAVAILABLE") from error

    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str,
        mime_type: str,
        prompt: str,
    ) -> ProviderTranscription:
        del mime_type, prompt
        started = perf_counter()
        suffix = Path(filename).suffix.lower() or ".webm"
        handle, temporary_path = tempfile.mkstemp(prefix="opic-audio-", suffix=suffix)
        try:
            model = await self._get_model()
            with os.fdopen(handle, "wb") as temporary_file:
                temporary_file.write(audio)
            result = await asyncio.to_thread(self._transcribe_file, model, temporary_path)
            record_usage_event(
                usage_event(
                    request_type="transcription",
                    model=self._settings.whisper_model,
                    latency_ms=round((perf_counter() - started) * 1000),
                    success=True,
                    retry_count=0,
                ),
                enabled=self._settings.detailed_usage_logging_enabled,
            )
            return result
        except (ProviderResponseError, ProviderUnavailableError) as error:
            with suppress(OSError):
                os.close(handle)
            record_usage_event(
                usage_event(
                    request_type="transcription",
                    model=self._settings.whisper_model,
                    latency_ms=round((perf_counter() - started) * 1000),
                    success=False,
                    retry_count=0,
                    error_type=str(error),
                ),
                enabled=self._settings.detailed_usage_logging_enabled,
            )
            raise
        finally:
            with suppress(OSError):
                Path(temporary_path).unlink(missing_ok=True)

    def _transcribe_file(self, model: Any, path: str) -> ProviderTranscription:
        try:
            segments_iter, _info = model.transcribe(
                path,
                language=self._settings.whisper_language,
                task="transcribe",
                beam_size=5,
                temperature=0.0,
                condition_on_previous_text=False,
                word_timestamps=True,
                vad_filter=self._settings.whisper_vad_enabled,
                vad_parameters={
                    "threshold": self._settings.whisper_vad_threshold,
                    "min_speech_duration_ms": (
                        self._settings.whisper_vad_min_speech_duration_ms
                    ),
                    "min_silence_duration_ms": (
                        self._settings.whisper_vad_min_silence_duration_ms
                    ),
                    "speech_pad_ms": self._settings.whisper_vad_speech_pad_ms,
                },
            )
            segment_values = list(segments_iter)
        except ProviderUnavailableError:
            raise
        except Exception as error:
            raise ProviderResponseError("TRANSCRIPTION_FAILED") from error

        segments: list[ProviderSegment] = []
        words: list[ProviderWord] = []
        transcript_parts: list[str] = []
        for segment in segment_values:
            text = str(getattr(segment, "text", ""))
            transcript_parts.append(text)
            segments.append(
                ProviderSegment(
                    text=text,
                    start=max(0.0, float(getattr(segment, "start", 0.0))),
                    end=max(0.0, float(getattr(segment, "end", 0.0))),
                )
            )
            for word in getattr(segment, "words", None) or ():
                word_text = str(getattr(word, "word", ""))
                if not word_text.strip():
                    continue
                words.append(
                    ProviderWord(
                        text=word_text,
                        start=max(0.0, float(getattr(word, "start", 0.0) or 0.0)),
                        end=max(0.0, float(getattr(word, "end", 0.0) or 0.0)),
                        probability=(
                            float(word.probability)
                            if getattr(word, "probability", None) is not None
                            else None
                        ),
                    )
                )

        text = "".join(transcript_parts).strip()
        if not text:
            raise ProviderResponseError("NO_SPEECH_DETECTED")
        return ProviderTranscription(
            text=text,
            model=self._settings.whisper_model,
            words=tuple(words),
            segments=tuple(segments),
        )

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def library_available(self) -> bool:
        return importlib.util.find_spec("faster_whisper") is not None

    @property
    def model_available(self) -> bool:
        configured = Path(self._settings.whisper_model)
        if configured.exists():
            return True
        cache_root = Path.home() / ".cache" / "huggingface" / "hub"
        model_folder = cache_root / (
            "models--Systran--faster-whisper-"
            + self._settings.whisper_model.replace("/", "--")
        )
        snapshots = model_folder / "snapshots"
        return snapshots.is_dir() and any(path.is_dir() for path in snapshots.iterdir())


class OllamaProvider(EvaluationProvider):
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport
        self._semaphore = asyncio.Semaphore(settings.ollama_max_concurrent_evaluations)

    async def evaluate(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, object],
        response_model: type[OutputModel],
        request_type: str = "evaluation",
        max_output_tokens: int | None = None,
        prompt_cache_key: str | None = None,
    ) -> ProviderEvaluation:
        del prompt_cache_key
        started = perf_counter()
        output_limit = max_output_tokens or self._settings.evaluation_max_output_tokens
        body = {
            "model": self._settings.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":")),
                },
            ],
            "format": response_model.model_json_schema(by_alias=True),
            "stream": False,
            "think": False,
            "keep_alive": self._settings.ollama_keep_alive,
            "options": {
                "temperature": 0,
                "num_ctx": self._settings.ollama_context_length,
                "num_predict": output_limit,
            },
        }
        timeout = httpx.Timeout(self._settings.ollama_timeout_seconds)
        retry_count = 0
        output: OutputModel | None = None
        payload: dict[str, Any] = {}
        while output is None:
            try:
                async with self._semaphore, httpx.AsyncClient(
                    timeout=timeout, transport=self._transport
                ) as client:
                    response = await client.post(
                        f"{self._settings.ollama_base_url.rstrip('/')}/api/chat",
                        json=body,
                    )
                    response.raise_for_status()
                    payload = response.json()
            except httpx.TimeoutException as error:
                self._record_failure(request_type, started, "OLLAMA_TIMEOUT", retry_count)
                raise ProviderUnavailableError("OLLAMA_TIMEOUT") from error
            except httpx.ConnectError as error:
                self._record_failure(request_type, started, "OLLAMA_UNAVAILABLE", retry_count)
                raise ProviderUnavailableError("OLLAMA_UNAVAILABLE") from error
            except httpx.HTTPStatusError as error:
                code = (
                    "OLLAMA_MODEL_UNAVAILABLE"
                    if error.response.status_code == 404
                    else "OLLAMA_ERROR"
                )
                self._record_failure(request_type, started, code, retry_count)
                raise ProviderUnavailableError(code) from error
            except (httpx.HTTPError, ValueError) as error:
                self._record_failure(request_type, started, "OLLAMA_ERROR", retry_count)
                raise ProviderUnavailableError("OLLAMA_ERROR") from error

            response_error = "EVALUATION_OUTPUT_TRUNCATED"
            validation_error: ValidationError | ValueError | None = None
            invalid_fields: list[str] = []
            invalid_content: str | None = None
            if payload.get("done_reason") != "length":
                content = payload.get("message", {}).get("content")
                if isinstance(content, str) and content.strip():
                    try:
                        output = response_model.model_validate_json(content)
                    except (ValidationError, ValueError) as error:
                        invalid_content = content
                        validation_error = error
                        response_error = "INVALID_EVALUATION_RESPONSE"
                        if isinstance(error, ValidationError):
                            invalid_fields = [
                                ".".join(str(part) for part in item["loc"])
                                for item in error.errors(
                                    include_url=False,
                                    include_input=False,
                                )
                            ]
                else:
                    response_error = "INVALID_EVALUATION_RESPONSE"

            if output is not None:
                break
            if retry_count >= self._settings.ollama_invalid_response_max_retries:
                self._record_failure(request_type, started, response_error, retry_count)
                raise ProviderResponseError(response_error) from validation_error

            retry_count += 1
            retry_messages: list[dict[str, str]] = []
            if invalid_content is not None:
                retry_messages.append({"role": "assistant", "content": invalid_content})
            retry_messages.append(
                {
                    "role": "user",
                    "content": (
                        "방금 JSON 전체를 스키마에 맞게 다시 출력하세요. 피드백, 설명, "
                        "상황 라벨, 단어 뜻, 강점과 blocker 제목, retry mission은 반드시 "
                        "자연스러운 한국어로 고쳐서 한글을 포함하세요. 한국어 문장 안의 "
                        "영어 예시 표현은 번역하지 말고 그대로 유지하세요. 추천 표현, 예문, "
                        "교정 전후 문장, 개선 답변과 전사 인용은 영어로 유지하세요. 각 답변 "
                        "배열 항목은 문장부호로 끝나는 완전한 영어 한 문장이어야 합니다. "
                        f"반드시 고쳐야 할 필드: {', '.join(invalid_fields) or '전체 JSON'}"
                    ),
                }
            )
            body["messages"] = [*body["messages"], *retry_messages]

        input_tokens = max(0, int(payload.get("prompt_eval_count", 0) or 0))
        output_tokens = max(0, int(payload.get("eval_count", 0) or 0))
        usage = UsageMetadata(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
        record_usage_event(
            usage_event(
                request_type=request_type,
                model=str(payload.get("model") or self._settings.ollama_model),
                latency_ms=round((perf_counter() - started) * 1000),
                success=True,
                retry_count=retry_count,
                usage=usage,
            ),
            enabled=self._settings.detailed_usage_logging_enabled,
        )
        return ProviderEvaluation(
            output=output,
            model=str(payload.get("model") or self._settings.ollama_model),
            usage=usage,
        )

    def _record_failure(
        self,
        request_type: str,
        started: float,
        code: str,
        retry_count: int = 0,
    ) -> None:
        record_usage_event(
            usage_event(
                request_type=request_type,
                model=self._settings.ollama_model,
                latency_ms=round((perf_counter() - started) * 1000),
                success=False,
                retry_count=retry_count,
                error_type=code,
            ),
            enabled=self._settings.detailed_usage_logging_enabled,
        )

    async def readiness(self) -> tuple[bool, bool, str | None]:
        timeout = httpx.Timeout(min(self._settings.ollama_timeout_seconds, 5))
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                version_response = await client.get(
                    f"{self._settings.ollama_base_url.rstrip('/')}/api/version"
                )
                version_response.raise_for_status()
                tags_response = await client.get(
                    f"{self._settings.ollama_base_url.rstrip('/')}/api/tags"
                )
                tags_response.raise_for_status()
                models = tags_response.json().get("models", [])
        except (httpx.HTTPError, ValueError):
            return False, False, None
        names = {
            str(item.get("name"))
            for item in models
            if isinstance(item, dict) and item.get("name")
        }
        return True, self._settings.ollama_model in names, self._settings.ollama_model


class LocalAiProvider:
    def __init__(self, settings: Settings) -> None:
        self.transcription = FasterWhisperProvider(settings)
        self.evaluation = OllamaProvider(settings)

    async def transcribe(self, **kwargs: Any) -> ProviderTranscription:
        return await self.transcription.transcribe(**kwargs)

    async def evaluate(self, **kwargs: Any) -> ProviderEvaluation:
        return await self.evaluation.evaluate(**kwargs)
