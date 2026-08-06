from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
