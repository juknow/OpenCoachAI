"""Legacy JSON report contracts; no scoring or I/O."""

from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel


class AggregateRetention(ApiModel):
    reference_items: int = Field(ge=0)
    hypothesis_items: int = Field(ge=0)
    matched_items: int = Field(ge=0)
    recall: float | None = Field(default=None, ge=0, le=1)
    precision: float | None = Field(default=None, ge=0, le=1)


class TranscriptionSampleScore(ApiModel):
    sample_id: str
    expected_behavior: Literal["transcribe", "empty-or-rejected", "rejected"]
    observed_status: Literal["transcribed", "rejected", "failed"]
    reference_words: int = Field(ge=0)
    hypothesis_words: int = Field(ge=0)
    word_errors: int = Field(ge=0)
    word_error_rate: float | None = Field(default=None, ge=0)
    filler: AggregateRetention
    repetition: AggregateRetention
    hallucinated_words: int = Field(ge=0)
    unexpected_outcome: bool
    latency_ms: int = Field(ge=0)
    error_code: str | None = None


class TranscriptionEvaluationReport(ApiModel):
    experiment_id: str
    dataset_version: str
    model: str
    prompt_version: str
    sample_count: int = Field(ge=1)
    speech_samples: int = Field(ge=0)
    failed_speech_samples: int = Field(ge=0)
    reference_words: int = Field(ge=0)
    word_errors: int = Field(ge=0)
    word_error_rate: float | None = Field(default=None, ge=0)
    filler: AggregateRetention
    repetition: AggregateRetention
    non_speech_samples: int = Field(ge=0)
    hallucination_samples: int = Field(ge=0)
    unexpected_outcome_samples: int = Field(ge=0)
    latency_p50_ms: int = Field(ge=0)
    latency_p95_ms: int = Field(ge=0)
    samples: list[TranscriptionSampleScore]
