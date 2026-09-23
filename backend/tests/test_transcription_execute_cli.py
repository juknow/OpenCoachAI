import json
from pathlib import Path

import pytest

from app.evals.transcription_dataset import TranscriptionDataset
from app.evals.transcription_execute_cli import execute_dataset, main
from app.providers.base import ProviderTranscription

WEBM = b"\x1aE\xdf\xa3" + b"0" * 1_024


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def transcribe(self, **_kwargs: object) -> ProviderTranscription:
        self.calls += 1
        return ProviderTranscription(
            text="Um, I I went there.",
            model="local-whisper/small.en",
            audio_seconds=4.25,
        )


def sample_files(tmp_path: Path) -> tuple[Path, TranscriptionDataset]:
    evaluation_dir = tmp_path / "transcription"
    samples_dir = evaluation_dir / "samples"
    samples_dir.mkdir(parents=True)
    (samples_dir / "answer.webm").write_bytes(WEBM)
    (samples_dir / "bad.webm").write_bytes(b"not webm" + b"0" * 1_024)
    payload = {
        "version": "stt-eval-v1",
        "samples": [
            {
                "id": "answer-001",
                "audioPath": "samples/answer.webm",
                "referenceTranscript": "Um, I I went there.",
                "tags": ["filler", "repetition"],
                "durationSeconds": 4.25,
                "language": "en",
                "source": "synthetic",
                "expectedBehavior": "transcribe",
            },
            {
                "id": "bad-001",
                "audioPath": "samples/bad.webm",
                "referenceTranscript": "",
                "tags": ["corrupt"],
                "durationSeconds": 0,
                "language": "en",
                "source": "synthetic",
                "expectedBehavior": "rejected",
            },
        ],
    }
    path = evaluation_dir / "manifest.local.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, TranscriptionDataset.model_validate(payload)


def test_dry_run_validates_files_without_loading_model(tmp_path: Path, capsys) -> None:
    manifest_path, _dataset = sample_files(tmp_path)
    output = manifest_path.parent / "results" / "run.json"

    assert main(
        [
            "--manifest", str(manifest_path),
            "--output", str(output),
            "--experiment-id", "local-small-001",
        ]
    ) == 0

    assert not output.exists()
    assert "Validated 2 samples" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_execute_dataset_reuses_service_and_produces_existing_run_contract(
    tmp_path: Path,
) -> None:
    manifest_path, dataset = sample_files(tmp_path)
    provider = FakeProvider()

    run = await execute_dataset(
        dataset=dataset,
        manifest_dir=manifest_path.parent,
        provider=provider,
        experiment_id="local-small-001",
        model_name="small.en",
        max_audio_bytes=5_000_000,
    )

    assert provider.calls == 1
    assert run.model == "local-whisper/small.en"
    assert run.config.max_audio_bytes == 5_000_000
    assert run.observations[0].transcript == "Um, I I went there."
    assert run.observations[0].audio_seconds == 4.25
    assert run.observations[1].status == "rejected"
    assert run.observations[1].error_code == "INVALID_AUDIO_DURATION"
    assert run.model_validate_json(run.model_dump_json(by_alias=True)) == run


def test_dry_run_rejects_output_outside_private_results(tmp_path: Path) -> None:
    manifest_path, _dataset = sample_files(tmp_path)

    with pytest.raises(SystemExit, match="2"):
        main(
            [
                "--manifest", str(manifest_path),
                "--output", str(tmp_path / "public.json"),
                "--experiment-id", "local-small-001",
            ]
        )


def test_dry_run_rejects_invalid_experiment_id_before_running(tmp_path: Path) -> None:
    manifest_path, _dataset = sample_files(tmp_path)

    with pytest.raises(SystemExit, match="2"):
        main(
            [
                "--manifest", str(manifest_path),
                "--output", str(manifest_path.parent / "results" / "run.json"),
                "--experiment-id", "Invalid ID",
                "--execute-live",
            ]
        )
