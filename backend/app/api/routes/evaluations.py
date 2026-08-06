from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_evaluation_provider, read_prompt
from app.config import Settings, get_settings
from app.errors import request_id_for
from app.providers.base import EvaluationProvider
from app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationV2Response,
    EvaluationV3Request,
    HigherAnswerRequest,
    HigherAnswerResponse,
)
from app.services.evaluation_service import EvaluationService
from app.services.evaluation_v2_service import EvaluationV2Service, HigherAnswerService

router = APIRouter(prefix="/api", tags=["evaluations"])


@router.post("/evaluations", response_model=EvaluationResponse)
async def create_evaluation(
    payload: EvaluationRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    provider: EvaluationProvider = Depends(get_evaluation_provider),
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


@router.post("/v2/evaluations", response_model=EvaluationV2Response)
async def create_evaluation_v2(
    payload: EvaluationRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    provider: EvaluationProvider = Depends(get_evaluation_provider),
) -> EvaluationV2Response:
    service = EvaluationV2Service(
        provider,
        read_prompt("evaluation_core.txt"),
        settings,
        request.app.state.evaluation_v2_cache,
    )
    return await service.evaluate(payload, request_id_for(request))


@router.post("/v3/evaluations", response_model=EvaluationV2Response)
async def create_evaluation_v3(
    payload: EvaluationV3Request,
    request: Request,
    settings: Settings = Depends(get_settings),
    provider: EvaluationProvider = Depends(get_evaluation_provider),
) -> EvaluationV2Response:
    service = EvaluationV2Service(
        provider,
        read_prompt("evaluation_core.txt"),
        settings,
        request.app.state.evaluation_v2_cache,
    )
    return await service.evaluate(payload.to_evaluation_request(), request_id_for(request))


@router.post("/v2/improvements/higher", response_model=HigherAnswerResponse)
async def create_higher_answer(
    payload: HigherAnswerRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    provider: EvaluationProvider = Depends(get_evaluation_provider),
) -> HigherAnswerResponse:
    service = HigherAnswerService(
        provider,
        read_prompt("higher_answer.txt"),
        settings,
        request.app.state.higher_answer_cache,
    )
    return await service.generate(payload, request_id_for(request))


@router.post("/v3/improvements/higher", response_model=HigherAnswerResponse)
async def create_higher_answer_v3(
    payload: HigherAnswerRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    provider: EvaluationProvider = Depends(get_evaluation_provider),
) -> HigherAnswerResponse:
    service = HigherAnswerService(
        provider,
        read_prompt("higher_answer.txt"),
        settings,
        request.app.state.higher_answer_cache,
    )
    return await service.generate(payload, request_id_for(request))
