from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError


class ApiProblem(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.message = message
        self.status_code = status_code


class ProviderResponseError(Exception):
    pass


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
    async def handle_rate_limit(request: Request, _error: RateLimitError) -> JSONResponse:
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
    async def handle_openai_status(request: Request, _error: APIStatusError) -> JSONResponse:
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
