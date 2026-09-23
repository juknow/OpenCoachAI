import asyncio
from collections.abc import Callable
from io import BytesIO
from typing import Any

from app.providers.base import ProviderTranscription


class LocalWhisperTranscriptionProvider:
    """Load a faster-whisper model only after the service has validated the audio."""

    def __init__(self, *, model_loader: Callable[[], Any], model_name: str) -> None:
        self._model_loader = model_loader
        self._model_name = model_name

    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str,
        mime_type: str,
        prompt: str,
    ) -> ProviderTranscription:
        # Whisper's initial_prompt is not equivalent to an instruction prompt.
        del filename, mime_type, prompt
        text, duration = await asyncio.to_thread(self._transcribe_sync, audio)
        return ProviderTranscription(
            text=text,
            model=f"local-whisper/{self._model_name}",
            audio_seconds=duration,
        )

    def _transcribe_sync(self, audio: bytes) -> tuple[str, float]:
        model = self._model_loader()
        with BytesIO(audio) as audio_stream:
            segments, info = model.transcribe(
                audio_stream,
                language="en",
                task="transcribe",
                vad_filter=False,
            )
            text = "".join(segment.text for segment in segments)
        return text, info.duration
