from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.stt_benchmark.contracts.evaluator import EvaluatorInput


@dataclass(frozen=True)
class SupportDecision:
    supported: bool
    reason: str | None = None

    @classmethod
    def yes(cls) -> SupportDecision:
        return cls(supported=True)

    @classmethod
    def no(cls, reason: str) -> SupportDecision:
        return cls(supported=False, reason=reason)


@dataclass(frozen=True)
class NativeEvaluatorOutput:
    payload: bytes
    suffix: str
    media_type: str

    def __post_init__(self) -> None:
        if not self.payload:
            raise ValueError("native evaluator output cannot be empty")
        if not self.suffix.startswith(".") or any(c in self.suffix for c in "/\\"):
            raise ValueError("native evaluator output suffix is invalid")


class EvaluatorFailure(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Evaluator(Protocol):
    evaluator_id: str
    evaluator_version: str
    normalization_profile: str
    required_inputs: frozenset[str]
    supported_metrics: frozenset[str]

    def supports(self, evaluator_input: EvaluatorInput) -> SupportDecision: ...

    async def evaluate(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput: ...


@dataclass(frozen=True)
class EvaluatorSettings:
    enabled_evaluators: tuple[str, ...]
    max_concurrency: int = 4

    def __post_init__(self) -> None:
        if not self.enabled_evaluators:
            raise ValueError("at least one evaluator must be enabled")
        if len(self.enabled_evaluators) != len(set(self.enabled_evaluators)):
            raise ValueError("enabled evaluator ids must be unique")
        if not 1 <= self.max_concurrency <= 32:
            raise ValueError("max concurrency must be between 1 and 32")
