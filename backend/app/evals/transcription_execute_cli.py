"""Run consented evaluation audio through the product's local Whisper path."""

import argparse
import asyncio
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

from app.config import Settings
from app.errors import ApiProblem
from app.evals.transcription_dataset import TranscriptionDataset, TranscriptionSample
from app.evals.transcription_run import (
    TranscriptionObservation,
    TranscriptionRun,
    TranscriptionRunConfig,
)
from app.providers.base import TranscriptionProvider
from app.services.transcription_processor import SUPPORTED_MIME_TYPES, TranscriptionProcessor

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


def _sample_path(manifest_dir: Path, sample: TranscriptionSample) -> Path:
    samples_dir = (manifest_dir / "samples").resolve()
    path = (manifest_dir / sample.audio_path).resolve()
    if not path.is_relative_to(samples_dir) or not path.is_file():
        raise ValueError(f"sample file is missing or outside samples/: {sample.id}")
    return path


def _mime_for_sample(sample: TranscriptionSample) -> str:
    suffix = Path(sample.audio_path).suffix.lower()
    return next(
        mime
        for mime, supported_suffix in SUPPORTED_MIME_TYPES.items()
        if supported_suffix == suffix
    )


async def execute_dataset(
    *,
    dataset: TranscriptionDataset,
    manifest_dir: Path,
    provider: TranscriptionProvider,
    experiment_id: str,
    model_name: str,
    max_audio_bytes: int,
) -> TranscriptionRun:
    processor = TranscriptionProcessor(
        provider=provider,
        settings=Settings(max_audio_bytes=max_audio_bytes),
        prompt="",  # Local Whisper does not use the product's OpenAI prompt.
    )
    observations: list[TranscriptionObservation] = []
    for sample in dataset.samples:
        path = _sample_path(manifest_dir, sample)
        audio = path.read_bytes()
        started = perf_counter()
        try:
            result = await processor.transcribe(
                audio=audio,
                filename=path.name,
                content_type=_mime_for_sample(sample),
                duration_seconds=sample.duration_seconds,
            )
        except ApiProblem as error:
            observations.append(
                TranscriptionObservation(
                    sample_id=sample.id,
                    status="rejected" if error.status_code < 500 else "failed",
                    latency_ms=round((perf_counter() - started) * 1_000),
                    error_code=error.code,
                )
            )
        except Exception:
            # Provider exceptions may contain private audio details; keep only a safe code.
            observations.append(
                TranscriptionObservation(
                    sample_id=sample.id,
                    status="failed",
                    latency_ms=round((perf_counter() - started) * 1_000),
                    error_code="LOCAL_STT_FAILED",
                )
            )
        else:
            observations.append(
                TranscriptionObservation(
                    sample_id=sample.id,
                    status="transcribed",
                    transcript=result.text,
                    latency_ms=round((perf_counter() - started) * 1_000),
                    usage=result.usage,
                    audio_seconds=result.audio_seconds,
                )
            )

    return TranscriptionRun(
        experiment_id=experiment_id,
        dataset_version=dataset.version,
        model=f"local-whisper/{model_name}",
        prompt_version="no-prompt-v1",
        created_at=datetime.now(UTC),
        config=TranscriptionRunConfig(max_audio_bytes=max_audio_bytes),
        observations=observations,
    )


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
            _sample_path(manifest_path.parent, sample)
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
