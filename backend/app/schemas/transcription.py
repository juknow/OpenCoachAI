from pydantic import Field

from app.schemas.common import ApiModel, ResponseMetadata


class TranscriptionMetadata(ResponseMetadata):
    audio_seconds: float | None = Field(default=None, ge=0)


class TranscriptionResponse(ApiModel):
    transcript: str
    metadata: TranscriptionMetadata
