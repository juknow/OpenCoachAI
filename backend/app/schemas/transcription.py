from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.evaluation import SpeechMetrics


class TranscriptionResponse(ApiModel):
    transcript: str
    request_id: str = Field(min_length=1)


class TranscriptionWord(ApiModel):
    text: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    probability: float | None = Field(default=None, ge=0, le=1)


class TranscriptionSegment(ApiModel):
    text: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)


class TranscriptionV3Response(ApiModel):
    raw_transcript: str
    speech_metrics: SpeechMetrics
    words: list[TranscriptionWord]
    segments: list[TranscriptionSegment]
    model: str
    request_id: str = Field(min_length=1)
