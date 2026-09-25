import asyncio
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.stt_benchmark.contracts.evaluator import EvaluatorInput
from app.stt_benchmark.evaluators.contract import (
    EvaluatorFailure,
    NativeEvaluatorOutput,
    SupportDecision,
)


def _resolve_executable(value: str | Path | None) -> Path | None:
    if value is None:
        located = shutil.which("sclite")
        return Path(located).resolve() if located else None
    candidate = Path(value).expanduser().resolve()
    return candidate if candidate.is_file() else None


class SctkEvaluator:
    evaluator_id = "nist-sctk"
    normalization_profile = "sctk-trn-native-v1"
    required_inputs = frozenset({"gold_text", "prediction_text", "sample_id"})
    supported_metrics = frozenset({"sclite_native_reports"})

    def __init__(self, executable: str | Path | None = None) -> None:
        self.executable = _resolve_executable(executable)
        if self.executable:
            digest = hashlib.sha256(self.executable.read_bytes()).hexdigest()[:16]
            self.evaluator_version = f"binary-sha256:{digest}"
        else:
            self.evaluator_version = "not-installed"

    def supports(self, evaluator_input: EvaluatorInput) -> SupportDecision:
        if self.executable is None:
            return SupportDecision.no("executable_not_found:sclite")
        return SupportDecision.yes()

    async def evaluate(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        return await asyncio.to_thread(self._evaluate_sync, evaluator_input)

    def _evaluate_sync(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        if self.executable is None:
            raise EvaluatorFailure("sclite_executable_unavailable")
        utterance_id = f"sample-{evaluator_input.sample_id}"
        with tempfile.TemporaryDirectory(prefix="opencoach-sctk-") as temporary:
            directory = Path(temporary)
            reference = directory / "reference.trn"
            hypothesis = directory / "hypothesis.trn"
            reference.write_text(
                f"{' '.join(evaluator_input.gold_text.splitlines())} ({utterance_id})\n",
                encoding="utf-8",
            )
            hypothesis.write_text(
                f"{' '.join(evaluator_input.prediction_text.splitlines())} ({utterance_id})\n",
                encoding="utf-8",
            )
            command = [
                str(self.executable),
                "-r",
                str(reference),
                "trn",
                "-h",
                str(hypothesis),
                "trn",
                "-i",
                "wsj",
                "-o",
                "all",
                "stdout",
            ]
            completed = subprocess.run(
                command,
                cwd=directory,
                capture_output=True,
                check=False,
                timeout=60,
            )
        if completed.returncode != 0:
            raise EvaluatorFailure(f"sclite_failed:exit_{completed.returncode}")
        if not completed.stdout:
            raise EvaluatorFailure("sclite_failed:empty_stdout")
        return NativeEvaluatorOutput(
            payload=completed.stdout,
            suffix=".txt",
            media_type="text/plain",
        )
