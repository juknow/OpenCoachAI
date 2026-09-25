from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import Field, model_validator

from app.schemas.common import ApiModel


class TranscriptSegment(ApiModel):
    words: str = Field(min_length=1, max_length=20_000)
    speaker: str | None = Field(default=None, min_length=1, max_length=100)
    start_time: float | None = Field(default=None, ge=0)
    end_time: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("segment startTime and endTime must be supplied together")
        if self.start_time is not None and self.end_time <= self.start_time:
            raise ValueError("segment endTime must be greater than startTime")
        return self


class EvaluationSupplement(ApiModel):
    sample_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    prediction_id: str | None = Field(default=None, min_length=1, max_length=200)
    gold_version: str | None = Field(default=None, min_length=1, max_length=200)
    prediction_version: str | None = Field(default=None, min_length=1, max_length=200)
    gold_intended_text: str | None = Field(default=None, max_length=20_000)
    prediction_intended_text: str | None = Field(default=None, max_length=20_000)
    reference_segments: tuple[TranscriptSegment, ...] | None = None
    prediction_segments: tuple[TranscriptSegment, ...] | None = None


class EvaluationSupplements(ApiModel):
    version: Literal["stt-evaluator-input-v1"] = "stt-evaluator-input-v1"
    samples: tuple[EvaluationSupplement, ...] = ()

    @model_validator(mode="after")
    def validate_unique_samples(self) -> Self:
        ids = [sample.sample_id for sample in self.samples]
        if len(ids) != len(set(ids)):
            raise ValueError("supplement sample ids must be unique")
        return self


class EvaluatorInput(ApiModel):
    experiment_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    sample_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    prediction_id: str
    gold_version: str
    prediction_version: str
    gold_text: str = Field(max_length=20_000)
    prediction_text: str = Field(max_length=20_000)
    expected_behavior: Literal["transcribe", "empty-or-rejected", "rejected"]
    observed_status: Literal["transcribed", "rejected", "failed"]
    language: Literal["en"]
    duration_seconds: float = Field(ge=0, le=120.5)
    latency_ms: int = Field(ge=0)
    error_code: str | None = None
    model: str
    prompt_version: str
    legacy_dataset_version: str
    gold_intended_text: str | None = Field(default=None, max_length=20_000)
    prediction_intended_text: str | None = Field(default=None, max_length=20_000)
    reference_segments: tuple[TranscriptSegment, ...] | None = None
    prediction_segments: tuple[TranscriptSegment, ...] | None = None


EvaluationExecutionStatus = Literal["success", "unsupported", "failed"]


class EvaluatorExecution(ApiModel):
    experiment_id: str
    evaluation_run_id: str
    sample_id: str
    prediction_id: str
    gold_version: str
    prediction_version: str
    evaluator_id: str
    evaluator_version: str
    normalization_profile: str
    started_at: datetime
    completed_at: datetime
    status: EvaluationExecutionStatus
    raw_result_path: str | None = None
    raw_result_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    raw_result_media_type: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_result_location(self) -> Self:
        result_fields = (
            self.raw_result_path,
            self.raw_result_sha256,
            self.raw_result_media_type,
        )
        if self.status == "success" and any(value is None for value in result_fields):
            raise ValueError("successful execution requires raw result metadata")
        if self.status != "success" and any(value is not None for value in result_fields):
            raise ValueError("non-successful execution cannot reference a raw result")
        if self.status == "success" and self.reason is not None:
            raise ValueError("successful execution cannot have a reason")
        if self.status != "success" and not self.reason:
            raise ValueError("non-successful execution requires a reason")
        return self


class EvaluationRunIndex(ApiModel):
    schema_version: Literal["stt-evaluator-index-v1"] = "stt-evaluator-index-v1"
    evaluation_run_id: str
    created_at: datetime
    max_concurrency: int = Field(ge=1, le=32)
    enabled_evaluators: tuple[str, ...]
    executions: tuple[EvaluatorExecution, ...]
