from typing import Literal

from app.schemas.common import ApiModel


class OllamaReadiness(ApiModel):
    running: bool
    model_available: bool
    model: str


class WhisperReadiness(ApiModel):
    library_available: bool
    model_available: bool
    model_loaded: bool
    model: str
    device: Literal["cpu"]
    compute_type: Literal["int8"]


class ReadinessResponse(ApiModel):
    provider: Literal["local"]
    ready: bool
    ollama: OllamaReadiness | None = None
    whisper: WhisperReadiness | None = None
    issues: list[str]
