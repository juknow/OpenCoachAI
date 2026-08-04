from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.api.dependencies import get_transcription_provider, read_prompt
from app.config import Settings, get_settings
from app.errors import request_id_for
from app.providers.base import TranscriptionProvider
from app.schemas.transcription import TranscriptionResponse, TranscriptionV3Response
from app.services.speech_metrics_service import calculate_speech_metrics
from app.services.transcription_service import TranscriptionService

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
    service = TranscriptionService(provider, settings, read_prompt("transcription.txt"))
    result = await service.transcribe(
        audio=content,
        filename=audio.filename,
        content_type=audio.content_type,
        duration_seconds=duration_seconds,
    )
    return TranscriptionResponse(transcript=result.text, request_id=request_id_for(request))


@router.post("/v3/transcriptions", response_model=TranscriptionV3Response)
async def create_transcription_v3(
    request: Request,
    audio: UploadFile = File(...),
    duration_seconds: float = Form(..., alias="durationSeconds"),
    attempt_number: int = Form(..., alias="attemptNumber", ge=1, le=2),
    settings: Settings = Depends(get_settings),
    provider: TranscriptionProvider = Depends(get_transcription_provider),
) -> TranscriptionV3Response:
    del attempt_number
    content = await audio.read(settings.max_audio_bytes + 1)
    service = TranscriptionService(provider, settings, read_prompt("transcription.txt"))
    result = await service.transcribe(
        audio=content,
        filename=audio.filename,
        content_type=audio.content_type,
        duration_seconds=duration_seconds,
    )
    return TranscriptionV3Response(
        raw_transcript=result.text,
        speech_metrics=calculate_speech_metrics(result, duration_seconds),
        words=[
            {
                "text": item.text,
                "start": item.start,
                "end": item.end,
                "probability": item.probability,
            }
            for item in result.words
        ],
        segments=[
            {"text": item.text, "start": item.start, "end": item.end}
            for item in result.segments
        ],
        model=result.model,
        request_id=request_id_for(request),
    )
