from pathlib import Path

from app.config import Settings
from app.errors import ApiProblem
from app.providers.base import AiProvider, ProviderTranscription

SUPPORTED_MIME_TYPES = {
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/x-m4a": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}


def normalized_mime_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def signature_matches(data: bytes, mime_type: str) -> bool:
    if mime_type == "audio/webm":
        return data.startswith(b"\x1aE\xdf\xa3")
    if mime_type in {"audio/mp4", "audio/x-m4a"}:
        return len(data) >= 12 and data[4:8] == b"ftyp"
    if mime_type in {"audio/wav", "audio/x-wav"}:
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    if mime_type in {"audio/mpeg", "audio/mp3"}:
        return data.startswith(b"ID3") or (
            len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0
        )
    return False


class TranscriptionService:
    def __init__(self, provider: AiProvider, settings: Settings, prompt: str) -> None:
        self._provider = provider
        self._settings = settings
        self._prompt = prompt

    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str | None,
        content_type: str | None,
        duration_seconds: float,
    ) -> ProviderTranscription:
        if duration_seconds < 5 or duration_seconds > 120.5:
            raise ApiProblem(
                "INVALID_AUDIO_DURATION", "녹음 길이는 5초 이상 120초 이하여야 합니다.", 422
            )
        if len(audio) < 512:
            raise ApiProblem("AUDIO_TOO_SMALL", "녹음 파일이 너무 작습니다.", 422)
        if len(audio) > self._settings.max_audio_bytes:
            raise ApiProblem("AUDIO_TOO_LARGE", "녹음 파일 크기가 허용 범위를 초과했습니다.", 413)

        mime_type = normalized_mime_type(content_type)
        suffix = SUPPORTED_MIME_TYPES.get(mime_type)
        if suffix is None:
            raise ApiProblem("UNSUPPORTED_AUDIO_TYPE", "지원하지 않는 녹음 파일 형식입니다.", 415)
        if not signature_matches(audio, mime_type):
            raise ApiProblem("INVALID_AUDIO_FILE", "녹음 파일 형식을 확인해 주세요.", 415)

        safe_stem = Path(filename or "recording").stem[:60] or "recording"
        return await self._provider.transcribe(
            audio=audio,
            filename=f"{safe_stem}{suffix}",
            mime_type=mime_type,
            prompt=self._prompt,
        )
