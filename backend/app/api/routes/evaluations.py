from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_ai_provider, read_prompt
from app.config import Settings, get_settings
from app.errors import request_id_for
from app.providers.base import AiProvider
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/api", tags=["evaluations"])


@router.post("/evaluations", response_model=EvaluationResponse)
async def create_evaluation(
    payload: EvaluationRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    provider: AiProvider = Depends(get_ai_provider),
) -> EvaluationResponse:
    prompt_filename = (
        "evaluation_v1.txt" if settings.evaluation_prompt_version == "v1" else "evaluation.txt"
    )
    service = EvaluationService(
        provider,
        read_prompt(prompt_filename),
        settings,
        request.app.state.evaluation_cache,
    )
    return await service.evaluate(payload, request_id_for(request))
