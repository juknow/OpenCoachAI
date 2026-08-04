from fastapi import APIRouter, Depends

from app.api.dependencies import get_ai_provider
from app.config import Settings, get_settings
from app.providers.base import AiProvider
from app.providers.local_provider import LocalAiProvider
from app.schemas.readiness import ReadinessResponse

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/readiness", response_model=ReadinessResponse)
async def readiness(
    settings: Settings = Depends(get_settings),
    provider: AiProvider = Depends(get_ai_provider),
) -> ReadinessResponse:
    if not isinstance(provider, LocalAiProvider):
        return ReadinessResponse(
            provider="local",
            ready=False,
            issues=["LOCAL_PROVIDER_UNAVAILABLE"],
        )

    ollama_running, model_available, _model = await provider.evaluation.readiness()
    whisper = provider.transcription
    issues: list[str] = []
    if not ollama_running:
        issues.append("OLLAMA_UNAVAILABLE")
    elif not model_available:
        issues.append("OLLAMA_MODEL_UNAVAILABLE")
    if not whisper.library_available:
        issues.append("WHISPER_NOT_INSTALLED")
    elif not whisper.model_available:
        issues.append("WHISPER_MODEL_UNAVAILABLE")
    return ReadinessResponse.model_validate(
        {
            "provider": "local",
            "ready": not issues,
            "ollama": {
                "running": ollama_running,
                "modelAvailable": model_available,
                "model": settings.ollama_model,
            },
            "whisper": {
                "libraryAvailable": whisper.library_available,
                "modelAvailable": whisper.model_available,
                "modelLoaded": whisper.loaded,
                "model": settings.whisper_model,
                "device": settings.whisper_device,
                "computeType": settings.whisper_compute_type,
            },
            "issues": issues,
        }
    )
