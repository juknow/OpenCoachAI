from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ApiModel

SUPPORTED_SAMPLE_SUFFIXES = frozenset({".webm", ".mp4", ".mp3", ".m4a", ".wav"})


class TranscriptionSample(ApiModel):
    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=3, max_length=80)
    audio_path: str = Field(min_length=1, max_length=240)
    reference_transcript: str = Field(max_length=20_000)
    tags: list[str] = Field(min_length=1, max_length=20)
    duration_seconds: float = Field(ge=0, le=120.5)
    language: Literal["en"] = "en"
    source: Literal["synthetic", "explicit-test-consent", "public-license"]
    expected_behavior: Literal["transcribe", "empty-or-rejected", "rejected"]

    @field_validator("audio_path")
    @classmethod
    def validate_audio_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("audioPath must be a safe relative path")
        if path.parts[0] != "samples":
            raise ValueError("audioPath must be located under samples/")
        if path.suffix.lower() not in SUPPORTED_SAMPLE_SUFFIXES:
            raise ValueError("audioPath has an unsupported audio suffix")
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("tags must be unique")
        for value in values:
            if not value or not value.replace("-", "").isalnum() or value != value.lower():
                raise ValueError("tags must use lowercase letters, numbers, and hyphens")
        return values

    @model_validator(mode="after")
    def validate_expected_transcript(self) -> Self:
        if self.expected_behavior == "transcribe":
            if self.duration_seconds <= 0:
                raise ValueError("transcribe samples must have a positive duration")
            if not self.reference_transcript.strip():
                raise ValueError("transcribe samples must have a reference transcript")
        return self


class TranscriptionDataset(ApiModel):
    version: str = Field(pattern=r"^stt-eval-v[1-9][0-9]*$")
    samples: list[TranscriptionSample] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_sample_ids(self) -> Self:
        sample_ids = [sample.id for sample in self.samples]
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError("sample ids must be unique")
        return self
