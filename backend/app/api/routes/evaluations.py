from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_ai_provider, read_prompt
from app.errors import request_id_for
from app.providers.base import AiProvider
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/api", tags=["evaluations"])


@router.post("/evaluations", response_model=EvaluationResponse)
async def create_evaluation(
    payload: EvaluationRequest,
    request: Request,
    provider: AiProvider = Depends(get_ai_provider),
) -> EvaluationResponse:
    service = EvaluationService(provider, read_prompt("evaluation.txt"))
    return await service.evaluate(payload, request_id_for(request))
