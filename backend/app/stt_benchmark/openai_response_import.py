"""Convert saved OpenAI JSON responses to a benchmark run without calling STT."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.stt_benchmark.contracts.dataset import TranscriptionDataset
from app.stt_benchmark.contracts.run import (
    TranscriptionObservation,
    TranscriptionRun,
    TranscriptionRunConfig,
)


def import_openai_responses(
    *,
    dataset: TranscriptionDataset,
    results_dir: Path,
    responses: dict[str, Path],
    experiment_id: str,
    model: str,
    prompt_version: str,
    prompt_hashes: dict[str, str] | None = None,
) -> TranscriptionRun:
    """Keep native JSON untouched; record its path/hash beside the copied text."""
    sample_ids = {sample.id for sample in dataset.samples}
    if sample_ids != responses.keys():
        raise ValueError("response sample IDs must exactly match the dataset")
    if prompt_hashes and not prompt_hashes.keys() <= sample_ids:
        raise ValueError("prompt hash has an unknown sample ID")

    root = results_dir.resolve()
    observations: list[TranscriptionObservation] = []
    for sample in dataset.samples:
        path = responses[sample.id].resolve()
        if not path.is_relative_to(root) or path.suffix.lower() != ".json":
            raise ValueError("response JSON must be inside the private results directory")
        raw = path.read_bytes()
        response = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(response, dict) or not isinstance(response.get("text"), str):
            raise ValueError("response JSON must contain a text string")
        observations.append(
            TranscriptionObservation(
                sample_id=sample.id,
                status="transcribed",
                transcript=response["text"],
                latency_ms=None,  # A saved API response cannot recover request latency.
                raw_response_path=path.relative_to(root).as_posix(),
                raw_response_sha256=hashlib.sha256(raw).hexdigest(),
                prompt_sha256=(prompt_hashes or {}).get(sample.id),
            )
        )

    return TranscriptionRun(
        experiment_id=experiment_id,
        dataset_version=dataset.version,
        model=f"openai/{model}",
        prompt_version=prompt_version,
        created_at=datetime.now(UTC),  # Import time, not the unknown API call time.
        config=TranscriptionRunConfig(language="en"),
        observations=observations,
    )
