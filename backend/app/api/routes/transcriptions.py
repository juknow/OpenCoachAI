from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.api.dependencies import get_transcription_provider, read_prompt
from app.config import Settings, get_settings
from app.errors import request_id_for
from app.providers.base import TranscriptionProvider
from app.schemas.transcription import TranscriptionMetadata, TranscriptionResponse
from app.services.transcription_processor import TranscriptionProcessor

router = APIRouter(prefix="/api", tags=["transcriptions"])


@router.post("/transcriptions", response_model=TranscriptionResponse)
async def create_transcription(
    request: Request,
    audio: UploadFile = File(...),
    duration_seconds: float = Form(..., alias="durationSeconds"),
    attempt_number: int = Form(..., alias="attemptNumber", ge=1, le=2),
    settings: Settings = Depends(get_settings),
    provider: TranscriptionProvider = Depends(get_transcription_provider),
) -> TranscriptionResponse:
    del attempt_number
    content = await audio.read(settings.max_audio_bytes + 1)
    processor = TranscriptionProcessor(provider, settings, read_prompt("transcription.txt"))
    result = await processor.transcribe(
        audio=content,
        filename=audio.filename,
        content_type=audio.content_type,
        duration_seconds=duration_seconds,
    )
    return TranscriptionResponse(
        transcript=result.text,
        metadata=TranscriptionMetadata(
            request_id=request_id_for(request),
            model=result.model,
            usage=result.usage,
            audio_seconds=result.audio_seconds,
        ),
    )
