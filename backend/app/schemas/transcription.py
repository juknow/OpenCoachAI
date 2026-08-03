from pydantic import Field

from app.schemas.common import ApiModel


class TranscriptionResponse(ApiModel):
    transcript: str
    request_id: str = Field(min_length=1)
