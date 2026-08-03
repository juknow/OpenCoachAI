from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config/status")
async def config_status(settings: Settings = Depends(get_settings)) -> dict[str, bool]:
    return {"openaiConfigured": settings.openai_configured}
