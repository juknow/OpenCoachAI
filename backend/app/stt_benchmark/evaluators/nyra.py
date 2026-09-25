import asyncio
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from app.stt_benchmark.contracts.evaluator import EvaluatorInput
from app.stt_benchmark.evaluators.contract import (
    EvaluatorFailure,
    NativeEvaluatorOutput,
    SupportDecision,
)

NYRA_SOURCE_FILES = ("evaluate.py", "normalize.py", "align.py", "tag.py")


class NyraEvaluator:
    evaluator_id = "nyra-verbatim"
    normalization_profile = "nyra-native-v1"
    required_inputs = frozenset(
        {"gold_text", "gold_intended_text", "prediction_text", "language"}
    )
    supported_metrics = frozenset(
        {
            "vWER",
            "vCER",
            "iWER",
            "iCER",
            "filler",
            "sound",
            "cutoff",
            "repetition",
            "disfluency_diagnostics",
        }
    )

    def __init__(self, checkout: str | Path | None = None) -> None:
        self.checkout = Path(checkout).expanduser().resolve() if checkout else None
        if self.checkout and all((self.checkout / name).is_file() for name in NYRA_SOURCE_FILES):
            digest = hashlib.sha256()
            for name in NYRA_SOURCE_FILES:
                digest.update((self.checkout / name).read_bytes())
            self.evaluator_version = f"source-sha256:{digest.hexdigest()[:16]}"
        else:
            self.evaluator_version = "checkout-not-configured"

    def supports(self, evaluator_input: EvaluatorInput) -> SupportDecision:
        if self.checkout is None or not all(
            (self.checkout / name).is_file() for name in NYRA_SOURCE_FILES
        ):
            return SupportDecision.no("nyra_checkout_not_configured")
        if evaluator_input.gold_intended_text is None:
            return SupportDecision.no("missing_input:gold_intended_text")
        return SupportDecision.yes()

    async def evaluate(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        return await asyncio.to_thread(self._evaluate_sync, evaluator_input)

    def _evaluate_sync(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        if self.checkout is None or evaluator_input.gold_intended_text is None:
            raise EvaluatorFailure("nyra_required_input_unavailable")
        bridge = Path(__file__).with_name("nyra_bridge.py")
        payload = {
            "sample_id": evaluator_input.sample_id,
            "language": evaluator_input.language,
            "gold_verbatim": evaluator_input.gold_text,
            "gold_intended": evaluator_input.gold_intended_text,
            "prediction_verbatim": evaluator_input.prediction_text,
            "prediction_intended": evaluator_input.prediction_intended_text,
        }
        with tempfile.TemporaryDirectory(prefix="opencoach-nyra-") as temporary:
            directory = Path(temporary)
            input_path = directory / "input.json"
            output_path = directory / "output.json"
            input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(bridge),
                    str(self.checkout),
                    str(input_path),
                    str(output_path),
                ],
                cwd=directory,
                capture_output=True,
                check=False,
                timeout=120,
            )
            if completed.returncode != 0 or not output_path.is_file():
                raise EvaluatorFailure(f"nyra_execution_failed:exit_{completed.returncode}")
            result = output_path.read_bytes()
        return NativeEvaluatorOutput(payload=result, suffix=".json", media_type="application/json")
