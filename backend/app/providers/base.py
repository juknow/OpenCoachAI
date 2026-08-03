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


@dataclass(frozen=True)
class ProviderEvaluation:
    output: BaseModel
    model: str
    usage: UsageMetadata | None


class AiProvider(Protocol):
    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str,
        mime_type: str,
        prompt: str,
    ) -> ProviderTranscription: ...

    async def evaluate(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, object],
        response_model: type[OutputModel],
    ) -> ProviderEvaluation: ...
