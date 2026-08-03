import logging
import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

logger = logging.getLogger("opic.openai")
SAFE_PROVIDER_LABEL = re.compile(r"^[A-Za-z0-9_.\[\]-]{1,160}$")
KNOWN_OPENAI_PARAMETERS = (
    "prompt_cache_breakpoint",
    "prompt_cache_options",
    "prompt_cache_key",
    "reasoning.effort",
    "max_output_tokens",
    "text.format",
    "text_format",
    "verbosity",
    "reasoning",
    "store",
)


class ApiProblem(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.message = message
        self.status_code = status_code


class ProviderResponseError(Exception):
    pass


def openai_error_field(error: APIStatusError, field: str) -> str | None:
    value = getattr(error, field, None)
    if isinstance(value, str) and value:
        return value

    body = getattr(error, "body", None)
    if not isinstance(body, dict):
        return None
    error_body = body.get("error", body)
    if not isinstance(error_body, dict):
        return None
    nested_value = error_body.get(field)
    return nested_value if isinstance(nested_value, str) and nested_value else None


def openai_error_parameter(error: APIStatusError) -> str | None:
    parameter = openai_error_field(error, "param")
    if parameter:
        return parameter

    # Some unsupported_parameter responses omit `param` even though the safe
    # parameter name is present in the SDK message. Extract only known request
    # field names and never return or log the raw provider message.
    message = getattr(error, "message", None)
    if not isinstance(message, str):
        return None
    return next((item for item in KNOWN_OPENAI_PARAMETERS if item in message), None)


def safe_provider_label(value: str | None) -> str:
    return value if value and SAFE_PROVIDER_LABEL.fullmatch(value) else "unknown"


def request_id_for(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unavailable"))


def error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "requestId": request_id_for(request),
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiProblem)
    async def handle_api_problem(request: Request, error: ApiProblem) -> JSONResponse:
        return error_response(request, error.status_code, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, _error: RequestValidationError) -> JSONResponse:
        return error_response(
            request,
            422,
            "INVALID_REQUEST",
            "요청 형식을 확인해 주세요.",
        )

    @app.exception_handler(RateLimitError)
    async def handle_rate_limit(request: Request, error: RateLimitError) -> JSONResponse:
        if openai_error_field(error, "code") == "insufficient_quota":
            return error_response(
                request,
                429,
                "OPENAI_QUOTA_EXCEEDED",
                "OpenAI API 크레딧 또는 프로젝트 사용 한도를 확인해 주세요.",
            )
        return error_response(
            request,
            429,
            "OPENAI_RATE_LIMITED",
            "AI 서비스 요청이 많습니다. 잠시 후 다시 시도해 주세요.",
        )

    @app.exception_handler(APITimeoutError)
    async def handle_timeout(request: Request, _error: APITimeoutError) -> JSONResponse:
        return error_response(
            request,
            504,
            "OPENAI_TIMEOUT",
            "AI 서비스 응답 시간이 초과되었습니다. 다시 시도해 주세요.",
        )

    @app.exception_handler(APIConnectionError)
    async def handle_connection(request: Request, _error: APIConnectionError) -> JSONResponse:
        return error_response(
            request,
            502,
            "OPENAI_UNAVAILABLE",
            "AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        )

    @app.exception_handler(APIStatusError)
    async def handle_openai_status(request: Request, error: APIStatusError) -> JSONResponse:
        status_code = int(getattr(error, "status_code", 0) or 0)
        provider_code = openai_error_field(error, "code")
        logger.warning(
            "openai_status_error status=%s code=%s param=%s request_id=%s",
            status_code,
            safe_provider_label(provider_code),
            safe_provider_label(openai_error_parameter(error)),
            request_id_for(request),
        )
        if status_code == 400:
            return error_response(
                request,
                502,
                "OPENAI_INVALID_REQUEST",
                "AI 평가 요청 형식이 현재 모델과 호환되지 않습니다. 백엔드 설정을 확인해 주세요.",
            )
        if status_code == 401:
            return error_response(
                request,
                502,
                "OPENAI_AUTHENTICATION_FAILED",
                "백엔드의 OpenAI API 키가 유효하지 않습니다. 서버 설정을 확인해 주세요.",
            )
        if status_code in {403, 404} or provider_code == "model_not_found":
            return error_response(
                request,
                502,
                "OPENAI_MODEL_UNAVAILABLE",
                "설정한 AI 평가 모델을 사용할 수 없습니다. "
                "프로젝트의 모델 권한과 모델명을 확인해 주세요.",
            )
        if status_code >= 500:
            return error_response(
                request,
                502,
                "OPENAI_UNAVAILABLE",
                "AI 서비스가 일시적으로 응답하지 않습니다. 잠시 후 다시 시도해 주세요.",
            )
        return error_response(
            request,
            502,
            "OPENAI_REQUEST_FAILED",
            "AI 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        )

    @app.exception_handler(ProviderResponseError)
    async def handle_provider_response(
        request: Request, error: ProviderResponseError
    ) -> JSONResponse:
        if str(error) == "OPENAI_NOT_CONFIGURED":
            return error_response(
                request,
                503,
                "OPENAI_NOT_CONFIGURED",
                "서버에 OpenAI API가 설정되지 않아 Demo Mode를 사용해야 합니다.",
            )
        if str(error) == "EVALUATION_OUTPUT_TRUNCATED":
            return error_response(
                request,
                502,
                "AI_OUTPUT_TRUNCATED",
                "AI 평가 응답이 출력 한도에 도달했습니다. 부분 결과는 저장되지 않았습니다.",
            )
        return error_response(
            request,
            502,
            "INVALID_AI_RESPONSE",
            "AI 응답을 검증하지 못했습니다. 다시 시도해 주세요.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, _error: Exception) -> JSONResponse:
        return error_response(
            request,
            500,
            "INTERNAL_ERROR",
            "요청 처리 중 오류가 발생했습니다.",
        )
