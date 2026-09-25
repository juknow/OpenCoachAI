"""Execute the legacy local-Whisper dataset using an injected provider.

No argument parsing or result-file writing occurs here. Product validation and
legacy failure semantics remain unchanged; multi-model raw capture comes later.
"""

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from app.config import Settings
from app.errors import ApiProblem
from app.providers.base import TranscriptionProvider
from app.services.transcription_processor import SUPPORTED_MIME_TYPES, TranscriptionProcessor
from app.stt_benchmark.contracts.dataset import TranscriptionDataset, TranscriptionSample
from app.stt_benchmark.contracts.run import (
    TranscriptionObservation,
    TranscriptionRun,
    TranscriptionRunConfig,
)


def sample_audio_path(manifest_dir: Path, sample: TranscriptionSample) -> Path:
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
        path = sample_audio_path(manifest_dir, sample)
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
