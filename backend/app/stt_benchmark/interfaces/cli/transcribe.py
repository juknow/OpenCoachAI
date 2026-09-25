"""Run consented evaluation audio through the product's local Whisper path."""

import argparse
import asyncio
import re
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from app.errors import ApiProblem
from app.stt_benchmark.contracts.dataset import TranscriptionDataset
from app.stt_benchmark.transcription_runner import execute_dataset, sample_audio_path

DEFAULT_MAX_AUDIO_BYTES = 5_000_000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate local STT samples or run them through local Whisper.",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--model", default="small.en")
    parser.add_argument("--max-audio-bytes", type=int, default=DEFAULT_MAX_AUDIO_BYTES)
    parser.add_argument("--execute-live", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    manifest_path = arguments.manifest.resolve()
    output_path = arguments.output.resolve()
    results_dir = (manifest_path.parent / "results").resolve()
    if not output_path.is_relative_to(results_dir) or output_path.suffix.lower() != ".json":
        parser.error("--output must be a JSON file under the manifest's results/ directory")
    if output_path.exists():
        parser.error("--output already exists; choose a new experiment result name")
    if not 1_024 <= arguments.max_audio_bytes <= 25_000_000:
        parser.error("--max-audio-bytes must be between 1024 and 25000000")
    if not arguments.model.strip():
        parser.error("--model must not be empty")
    if len(f"local-whisper/{arguments.model}") > 160:
        parser.error("--model is too long for the run JSON contract")
    if (
        not 3 <= len(arguments.experiment_id) <= 100
        or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", arguments.experiment_id) is None
    ):
        parser.error("--experiment-id must use 3-100 lowercase letters, numbers, or hyphens")

    try:
        dataset = TranscriptionDataset.model_validate_json(
            manifest_path.read_text(encoding="utf-8-sig")
        )
        for sample in dataset.samples:
            sample_audio_path(manifest_path.parent, sample)
    except (OSError, ValidationError, ValueError):
        parser.error("manifest or sample files are invalid; check their paths and schema")

    if not arguments.execute_live:
        print(f"Validated {len(dataset.samples)} samples; add --execute-live to run local STT.")
        return 0

    from app.api.dependencies import load_local_whisper_model
    from app.providers.local_whisper_provider import LocalWhisperTranscriptionProvider

    try:
        load_local_whisper_model(arguments.model)
    except ApiProblem:
        parser.error("local Whisper model is unavailable; check the model cache")
    provider = LocalWhisperTranscriptionProvider(
        model_loader=lambda: load_local_whisper_model(arguments.model),
        model_name=arguments.model,
    )
    run = asyncio.run(
        execute_dataset(
            dataset=dataset,
            manifest_dir=manifest_path.parent,
            provider=provider,
            experiment_id=arguments.experiment_id,
            model_name=arguments.model,
            max_audio_bytes=arguments.max_audio_bytes,
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("x", encoding="utf-8") as output_file:
            output_file.write(run.model_dump_json(by_alias=True, indent=2) + "\n")
    except FileExistsError:
        parser.error("--output already exists; choose a new experiment result name")
    print(f"Saved {len(run.observations)} observations to {output_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
