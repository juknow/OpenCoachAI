from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.schemas.common import UsageMetadata

OutputModel = TypeVar("OutputModel", bound=BaseModel)


@dataclass(frozen=True)
class ProviderTranscription:
    text: str
    model: str
    usage: UsageMetadata | None = None
    words: tuple["ProviderWord", ...] = ()
    segments: tuple["ProviderSegment", ...] = ()


@dataclass(frozen=True)
class ProviderWord:
    text: str
    start: float
    end: float
    probability: float | None = None


@dataclass(frozen=True)
class ProviderSegment:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class ProviderEvaluation:
    output: BaseModel
    model: str
    usage: UsageMetadata | None


class TranscriptionProvider(Protocol):
    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str,
        mime_type: str,
        prompt: str,
    ) -> ProviderTranscription: ...



class EvaluationProvider(Protocol):
    async def evaluate(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, object],
        response_model: type[OutputModel],
        request_type: str = "evaluation",
        max_output_tokens: int | None = None,
        prompt_cache_key: str | None = None,
    ) -> ProviderEvaluation: ...


class AiProvider(TranscriptionProvider, EvaluationProvider, Protocol):
    pass
