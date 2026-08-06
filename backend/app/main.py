from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import evaluations, health, readiness, transcriptions
from app.config import get_settings
from app.errors import register_error_handlers
from app.evaluation_cache import EvaluationCache
from app.schemas.evaluation import EvaluationResponse, EvaluationV2Response, HigherAnswerResponse


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="OPIc Coach API", version="1.0.0")
    application.state.evaluation_cache = EvaluationCache[EvaluationResponse](
        ttl_seconds=settings.evaluation_cache_ttl_seconds,
        max_entries=settings.evaluation_cache_max_entries,
    )
    application.state.evaluation_v2_cache = EvaluationCache[EvaluationV2Response](
        ttl_seconds=settings.evaluation_cache_ttl_seconds,
        max_entries=settings.evaluation_cache_max_entries,
    )
    application.state.higher_answer_cache = EvaluationCache[HigherAnswerResponse](
        ttl_seconds=settings.evaluation_cache_ttl_seconds,
        max_entries=settings.evaluation_cache_max_entries,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )

    @application.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    application.include_router(health.router)
    application.include_router(readiness.router)
    application.include_router(transcriptions.router)
    application.include_router(evaluations.router)
    register_error_handlers(application)
    return application


app = create_app()
