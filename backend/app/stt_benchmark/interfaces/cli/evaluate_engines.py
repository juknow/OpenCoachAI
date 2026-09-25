import argparse
import asyncio
import re
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from app.stt_benchmark.contracts.dataset import TranscriptionDataset
from app.stt_benchmark.contracts.evaluator import EvaluationSupplements
from app.stt_benchmark.contracts.run import TranscriptionRun
from app.stt_benchmark.evaluation_orchestrator import EvaluationOrchestrator
from app.stt_benchmark.evaluator_inputs import build_evaluator_inputs
from app.stt_benchmark.evaluators.contract import EvaluatorSettings
from app.stt_benchmark.evaluators.registry import create_evaluator_registry
from app.stt_benchmark.storage.artifacts import EvaluationArtifactStore

DEFAULT_EVALUATORS = "custom,jiwer"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run independent evaluators against saved Gold and Prediction JSON.",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evaluation-run-id", required=True)
    parser.add_argument("--evaluators", default=DEFAULT_EVALUATORS)
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument("--supplements", type=Path)
    parser.add_argument("--sctk-executable", type=Path)
    parser.add_argument("--nyra-checkout", type=Path)
    parser.add_argument("--huggingface-cache-dir", type=Path)
    return parser


def _evaluator_ids(value: str, all_ids: tuple[str, ...]) -> tuple[str, ...]:
    if value.strip().lower() == "all":
        return all_ids
    ids = tuple(part.strip() for part in value.split(",") if part.strip())
    if not ids:
        raise ValueError("--evaluators must contain at least one evaluator id")
    return ids


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    manifest_path = arguments.manifest.resolve()
    output_dir = arguments.output_dir.resolve()
    private_results = (manifest_path.parent / "results").resolve()
    if not output_dir.is_relative_to(private_results):
        parser.error("--output-dir must be under the manifest's private results/ directory")
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", arguments.evaluation_run_id) is None:
        parser.error("--evaluation-run-id must use lowercase letters, numbers, and hyphens")

    try:
        dataset = TranscriptionDataset.model_validate_json(
            manifest_path.read_text(encoding="utf-8-sig")
        )
        run = TranscriptionRun.model_validate_json(arguments.run.read_text(encoding="utf-8-sig"))
        supplements = (
            EvaluationSupplements.model_validate_json(
                arguments.supplements.read_text(encoding="utf-8-sig")
            )
            if arguments.supplements
            else None
        )
        inputs = build_evaluator_inputs(dataset, run, supplements)
        registry = create_evaluator_registry(
            sctk_executable=arguments.sctk_executable,
            nyra_checkout=arguments.nyra_checkout,
            huggingface_cache_directory=arguments.huggingface_cache_dir,
        )
        evaluator_ids = _evaluator_ids(arguments.evaluators, registry.ids)
        settings = EvaluatorSettings(
            enabled_evaluators=evaluator_ids,
            max_concurrency=arguments.max_concurrency,
        )
        orchestrator = EvaluationOrchestrator(
            registry,
            settings,
            EvaluationArtifactStore(output_dir, arguments.evaluation_run_id),
        )
        index = asyncio.run(orchestrator.run(inputs, arguments.evaluation_run_id))
    except (OSError, ValidationError, ValueError) as error:
        parser.error(str(error))

    index_path = output_dir / arguments.evaluation_run_id / "index.json"
    successful = sum(item.status == "success" for item in index.executions)
    unsupported = sum(item.status == "unsupported" for item in index.executions)
    failed = sum(item.status == "failed" for item in index.executions)
    print(
        f"Saved evaluator index to {index_path} "
        f"(success={successful}, unsupported={unsupported}, failed={failed})."
    )
    return 0
