import re
from collections.abc import Iterable
from pathlib import Path

from app.stt_benchmark.evaluators.contract import Evaluator
from app.stt_benchmark.evaluators.custom import CustomEvaluator
from app.stt_benchmark.evaluators.huggingface_evaluate import HuggingFaceEvaluateEvaluator
from app.stt_benchmark.evaluators.jiwer_evaluator import JiwerEvaluator
from app.stt_benchmark.evaluators.meeteval_evaluator import MeetEvalEvaluator
from app.stt_benchmark.evaluators.nyra import NyraEvaluator
from app.stt_benchmark.evaluators.sctk import SctkEvaluator


class EvaluatorRegistry:
    def __init__(self, evaluators: Iterable[Evaluator]) -> None:
        evaluator_items = tuple(evaluators)
        invalid_ids = [
            evaluator.evaluator_id
            for evaluator in evaluator_items
            if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", evaluator.evaluator_id) is None
        ]
        if invalid_ids:
            raise ValueError(f"invalid evaluator ids: {invalid_ids}")
        self._evaluators = {evaluator.evaluator_id: evaluator for evaluator in evaluator_items}
        if len(self._evaluators) == 0:
            raise ValueError("the evaluator registry cannot be empty")
        if len(self._evaluators) != len(evaluator_items):
            raise ValueError("evaluator ids must be unique")

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self._evaluators)

    def select(self, evaluator_ids: tuple[str, ...]) -> tuple[Evaluator, ...]:
        unknown = sorted(set(evaluator_ids) - self._evaluators.keys())
        if unknown:
            raise ValueError(f"unknown evaluator ids: {unknown}")
        return tuple(self._evaluators[evaluator_id] for evaluator_id in evaluator_ids)


def create_evaluator_registry(
    *,
    sctk_executable: str | Path | None = None,
    nyra_checkout: str | Path | None = None,
    huggingface_cache_directory: str | Path | None = None,
) -> EvaluatorRegistry:
    return EvaluatorRegistry(
        (
            CustomEvaluator(),
            JiwerEvaluator(),
            NyraEvaluator(nyra_checkout),
            SctkEvaluator(sctk_executable),
            HuggingFaceEvaluateEvaluator(cache_directory=huggingface_cache_directory),
            MeetEvalEvaluator(),
        )
    )
