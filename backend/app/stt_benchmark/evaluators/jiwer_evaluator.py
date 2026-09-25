import asyncio
import importlib.util
import json
from importlib.metadata import PackageNotFoundError, version

from app.stt_benchmark.contracts.evaluator import EvaluatorInput
from app.stt_benchmark.evaluators.contract import (
    EvaluatorFailure,
    NativeEvaluatorOutput,
    SupportDecision,
)


def _package_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "not-installed"


class JiwerEvaluator:
    evaluator_id = "jiwer"
    normalization_profile = "verbatim-whitespace-v1"
    required_inputs = frozenset({"gold_text", "prediction_text"})
    supported_metrics = frozenset({"wer", "cer", "word_alignment", "character_alignment"})

    def __init__(self) -> None:
        self.evaluator_version = _package_version("jiwer")

    def supports(self, evaluator_input: EvaluatorInput) -> SupportDecision:
        if importlib.util.find_spec("jiwer") is None:
            return SupportDecision.no("dependency_not_installed:jiwer")
        return SupportDecision.yes()

    async def evaluate(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        return await asyncio.to_thread(self._evaluate_sync, evaluator_input)

    @staticmethod
    def _evaluate_sync(evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        try:
            import jiwer

            word_transform = jiwer.Compose(
                [
                    jiwer.RemoveMultipleSpaces(),
                    jiwer.Strip(),
                    jiwer.ReduceToListOfListOfWords(),
                ]
            )
            word = jiwer.process_words(
                evaluator_input.gold_text,
                evaluator_input.prediction_text,
                reference_transform=word_transform,
                hypothesis_transform=word_transform,
            )
            character = jiwer.process_characters(
                evaluator_input.gold_text,
                evaluator_input.prediction_text,
            )
        except Exception as error:
            raise EvaluatorFailure(f"jiwer_execution_failed:{type(error).__name__}") from error

        def alignment(chunks: list[object]) -> list[dict[str, object]]:
            return [
                {
                    "type": chunk.type,
                    "ref_start_idx": chunk.ref_start_idx,
                    "ref_end_idx": chunk.ref_end_idx,
                    "hyp_start_idx": chunk.hyp_start_idx,
                    "hyp_end_idx": chunk.hyp_end_idx,
                }
                for chunk in chunks
            ]

        def result(value: object, rate_name: str) -> dict[str, object]:
            data: dict[str, object] = {
                rate_name: getattr(value, rate_name),
                "hits": value.hits,
                "substitutions": value.substitutions,
                "insertions": value.insertions,
                "deletions": value.deletions,
                "references": value.references,
                "hypotheses": value.hypotheses,
                "alignments": [alignment(chunks) for chunks in value.alignments],
            }
            for name in ("mer", "wil", "wip"):
                if hasattr(value, name):
                    data[name] = getattr(value, name)
            return data

        payload = json.dumps(
            {"word": result(word, "wer"), "character": result(character, "cer")},
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        return NativeEvaluatorOutput(payload=payload, suffix=".json", media_type="application/json")
