import asyncio
from io import BytesIO
from typing import Any

from app.providers.base import ProviderTranscription


class LocalWhisperTranscriptionProvider:
    """Adapt an already loaded faster-whisper model to the transcription contract."""

    def __init__(self, *, model: Any, model_name: str) -> None:
        self._model = model
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
        with BytesIO(audio) as audio_stream:
            segments, info = self._model.transcribe(
                audio_stream,
                language="en",
                task="transcribe",
                vad_filter=False,
            )
            text = "".join(segment.text for segment in segments)
        return text, info.duration
