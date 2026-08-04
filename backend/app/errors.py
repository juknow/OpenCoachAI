from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiProblem(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.message = message
        self.status_code = status_code


class ProviderResponseError(Exception):
    pass


class ProviderUnavailableError(Exception):
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
        return error_response(request, 422, "INVALID_REQUEST", "요청 형식을 확인해 주세요.")

    @app.exception_handler(ProviderResponseError)
    async def handle_provider_response(
        request: Request, error: ProviderResponseError
    ) -> JSONResponse:
        code = str(error)
        if code == "EVALUATION_OUTPUT_TRUNCATED":
            return error_response(
                request,
                502,
                "AI_OUTPUT_TRUNCATED",
                "AI 평가 응답이 출력 한도에 도달했습니다. 부분 결과는 저장되지 않았습니다.",
            )
        if code == "NO_SPEECH_DETECTED":
            return error_response(
                request,
                422,
                "NO_SPEECH_DETECTED",
                "녹음에서 영어 발화를 확인하지 못했습니다. 마이크와 녹음 내용을 확인해 주세요.",
            )
        if code == "TRANSCRIPTION_FAILED":
            return error_response(
                request,
                422,
                "TRANSCRIPTION_FAILED",
                "로컬 음성 전사를 완료하지 못했습니다. 녹음 파일 상태를 확인해 주세요.",
            )
        return error_response(
            request,
            502,
            "INVALID_AI_RESPONSE",
            "로컬 AI 응답을 검증하지 못했습니다. 다시 시도해 주세요.",
        )

    @app.exception_handler(ProviderUnavailableError)
    async def handle_provider_unavailable(
        request: Request, error: ProviderUnavailableError
    ) -> JSONResponse:
        code = str(error)
        messages = {
            "OLLAMA_UNAVAILABLE": (
                "Ollama가 실행 중이지 않습니다. Ollama를 시작한 뒤 다시 시도해 주세요."
            ),
            "OLLAMA_MODEL_UNAVAILABLE": "설정된 Ollama 모델이 설치되어 있지 않습니다.",
            "OLLAMA_TIMEOUT": "로컬 AI 평가 시간이 초과되었습니다. 다시 시도해 주세요.",
            "OLLAMA_ERROR": "Ollama가 평가 요청을 처리하지 못했습니다.",
            "WHISPER_NOT_INSTALLED": "faster-whisper가 설치되어 있지 않습니다.",
            "WHISPER_MODEL_UNAVAILABLE": "설정된 Whisper 모델을 로컬에서 찾지 못했습니다.",
        }
        safe_code = code if code in messages else "LOCAL_PROVIDER_UNAVAILABLE"
        return error_response(
            request,
            503,
            safe_code,
            messages.get(code, "로컬 AI 서비스를 사용할 수 없습니다."),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, _error: Exception) -> JSONResponse:
        return error_response(
            request,
            500,
            "INTERNAL_ERROR",
            "요청 처리 중 오류가 발생했습니다.",
        )
