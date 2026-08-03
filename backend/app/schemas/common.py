from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class PracticeLevel(StrEnum):
    NL = "NL"
    NM = "NM"
    NH = "NH"
    IL = "IL"
    IM1 = "IM1"
    IM2 = "IM2"
    IM3 = "IM3"
    IH = "IH"
    AL = "AL"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuestionType(StrEnum):
    DESCRIPTION = "description"
    ROUTINE = "routine"
    PAST_EXPERIENCE = "past_experience"
    COMPARISON_CHANGE = "comparison_change"
    ROLE_PLAY = "role_play"
    PROBLEM_SOLUTION = "problem_solution"


class UsageMetadata(ApiModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class ResponseMetadata(ApiModel):
    request_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    usage: UsageMetadata | None = None


class ApiError(ApiModel):
    code: str
    message: str
    request_id: str


class ApiErrorResponse(ApiModel):
    error: ApiError
