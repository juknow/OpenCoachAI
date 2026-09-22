from datetime import datetime
from typing import Literal, Self

from pydantic import Field, model_validator

from app.schemas.common import ApiModel, UsageMetadata


class TranscriptionRunConfig(ApiModel):
    language: Literal["en"] = "en"
    chunking: Literal["none", "auto"] = "none"
    temperature: float | None = Field(default=None, ge=0, le=1)
    include_logprobs: bool = False
    prompt_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    timeout_seconds: float | None = Field(default=None, ge=5, le=180)
    max_retries: int | None = Field(default=None, ge=0, le=2)
    max_audio_bytes: int | None = Field(default=None, ge=1_024, le=25_000_000)


class TranscriptionObservation(ApiModel):
    sample_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    status: Literal["transcribed", "rejected", "failed"]
    transcript: str = Field(default="", max_length=20_000)
    latency_ms: int = Field(ge=0)
    error_code: str | None = Field(
        default=None,
        pattern=r"^[A-Z][A-Z0-9_]*$",
        max_length=100,
    )
    usage: UsageMetadata | None = None
    audio_seconds: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_status_payload(self) -> Self:
        if self.status == "transcribed" and self.error_code is not None:
            raise ValueError("transcribed observations cannot have an error code")
        if self.status != "transcribed":
            if self.transcript.strip():
                raise ValueError("rejected or failed observations cannot have a transcript")
            if self.error_code is None:
                raise ValueError("rejected or failed observations require an error code")
        return self


class TranscriptionRun(ApiModel):
    experiment_id: str = Field(
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        min_length=3,
        max_length=100,
    )
    dataset_version: str = Field(pattern=r"^stt-eval-v[1-9][0-9]*$")
    model: str = Field(min_length=1, max_length=160)
    prompt_version: str = Field(
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        min_length=3,
        max_length=100,
    )
    created_at: datetime
    config: TranscriptionRunConfig
    observations: list[TranscriptionObservation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_sample_ids(self) -> Self:
        sample_ids = [observation.sample_id for observation in self.observations]
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError("observation sample ids must be unique")
        return self

