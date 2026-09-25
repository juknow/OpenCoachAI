import hashlib
import json
import re
from pathlib import Path

from app.stt_benchmark.contracts.evaluator import EvaluationRunIndex
from app.stt_benchmark.evaluators.contract import NativeEvaluatorOutput


class EvaluationArtifactStore:
    """Write one immutable directory per evaluation run."""

    def __init__(self, root: Path, evaluation_run_id: str) -> None:
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", evaluation_run_id) is None:
            raise ValueError("evaluation run id must use lowercase letters, numbers, and hyphens")
        self.root = root.resolve()
        self.evaluation_run_id = evaluation_run_id
        self.run_directory = self.root / evaluation_run_id

    def create(self) -> None:
        self.run_directory.mkdir(parents=True, exist_ok=False)

    def write_native_result(
        self,
        *,
        sample_id: str,
        evaluator_id: str,
        output: NativeEvaluatorOutput,
    ) -> tuple[str, str]:
        target_directory = self.run_directory / "raw" / sample_id
        target_directory.mkdir(parents=True, exist_ok=True)
        target = target_directory / f"{evaluator_id}{output.suffix}"
        with target.open("xb") as result_file:
            result_file.write(output.payload)
        relative = target.relative_to(self.run_directory).as_posix()
        digest = hashlib.sha256(output.payload).hexdigest()
        return relative, digest

    def write_index(self, index: EvaluationRunIndex) -> Path:
        target = self.run_directory / "index.json"
        payload = json.dumps(
            index.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            indent=2,
        )
        with target.open("x", encoding="utf-8") as index_file:
            index_file.write(payload + "\n")
        return target
