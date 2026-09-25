import asyncio
import hashlib
import importlib.util
import json
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from app.stt_benchmark.contracts.evaluator import EvaluatorInput
from app.stt_benchmark.evaluators.contract import (
    EvaluatorFailure,
    NativeEvaluatorOutput,
    SupportDecision,
)


class HuggingFaceEvaluateEvaluator:
    evaluator_id = "huggingface-evaluate"
    normalization_profile = "huggingface-metric-native-v1"
    required_inputs = frozenset({"gold_text", "prediction_text"})
    supported_metrics = frozenset({"wer", "cer"})

    def __init__(
        self,
        loader: Callable[[str], Any] | None = None,
        cache_directory: str | Path | None = None,
    ) -> None:
        self._loader = loader
        self._cache_directory = (
            Path(cache_directory).expanduser().resolve() if cache_directory else None
        )
        # Evaluate's dynamic metric loader is not thread-safe inside one process.
        # Keep this adapter serial while other evaluator adapters still run in parallel.
        self._execution_lock = asyncio.Lock()
        try:
            self.evaluator_version = version("evaluate")
        except PackageNotFoundError:
            self.evaluator_version = "not-installed"

    def supports(self, evaluator_input: EvaluatorInput) -> SupportDecision:
        if self._loader is None and importlib.util.find_spec("evaluate") is None:
            return SupportDecision.no("dependency_not_installed:evaluate")
        if not evaluator_input.gold_text.strip():
            return SupportDecision.no("empty_reference_not_supported:huggingface-wer")
        return SupportDecision.yes()

    async def evaluate(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        async with self._execution_lock:
            return await asyncio.to_thread(self._evaluate_sync, evaluator_input)

    def _evaluate_sync(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        try:
            loader = self._loader
            if loader is None:
                import evaluate

                experiment_key = ":".join(
                    (
                        evaluator_input.experiment_id,
                        evaluator_input.sample_id,
                        evaluator_input.prediction_id,
                    )
                ).encode("utf-8")
                experiment_id = f"opencoach-{hashlib.sha256(experiment_key).hexdigest()[:16]}"
                load_arguments = (
                    {"cache_dir": str(self._cache_directory)}
                    if self._cache_directory is not None
                    else {}
                )
                wer_metric = evaluate.load(
                    "wer", experiment_id=experiment_id, **load_arguments
                )
                cer_metric = evaluate.load(
                    "cer", experiment_id=experiment_id, **load_arguments
                )
            else:
                wer_metric = loader("wer")
                cer_metric = loader("cer")
            arguments = {
                "predictions": [evaluator_input.prediction_text],
                "references": [evaluator_input.gold_text],
            }
            native = {
                "wer": wer_metric.compute(**arguments),
                "cer": cer_metric.compute(**arguments),
            }
        except Exception as error:
            raise EvaluatorFailure(
                f"huggingface_evaluate_failed:{type(error).__name__}"
            ) from error
        payload = json.dumps(native, ensure_ascii=False, indent=2).encode("utf-8")
        return NativeEvaluatorOutput(payload=payload, suffix=".json", media_type="application/json")
