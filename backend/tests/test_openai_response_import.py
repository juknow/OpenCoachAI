import hashlib
import json
from pathlib import Path

import pytest

from app.stt_benchmark.__main__ import main
from app.stt_benchmark.contracts.run import TranscriptionRun


def _private_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "transcription"
    results = root / "results"
    raw = results / "predictions" / "openai-gpt-transcribe-001" / "raw"
    raw.mkdir(parents=True)
    manifest = root / "manifest.local.json"
    manifest.write_text(
        json.dumps(
            {
                "version": "stt-eval-v1",
                "samples": [
                    {
                        "id": sample_id,
                        "audioPath": f"samples/{sample_id}.m4a",
                        "referenceTranscript": reference,
                        "tags": ["verbatim"],
                        "durationSeconds": 4,
                        "source": "synthetic",
                        "expectedBehavior": "transcribe",
                    }
                    for sample_id, reference in (
                        ("park-001", "Um, I I went to the park."),
                        ("travel-001", "I wan- wanted to travel."),
                    )
                ],
            }
        ),
        encoding="utf-8",
    )
    park = raw / "park-001.json"
    travel = raw / "travel-001.json"
    park.write_text(
        json.dumps(
            {"text": "Um, I I went to the park.", "usage": {"type": "duration", "seconds": 4}}
        ),
        encoding="utf-8",
    )
    travel.write_text(
        json.dumps({"text": "I wanted to travel.", "languages": [{"code": "en"}]}),
        encoding="utf-8",
    )
    return manifest, results, park, travel


def _import_args(manifest: Path, results: Path, park: Path, travel: Path) -> list[str]:
    return [
        "import-openai",
        "--manifest", str(manifest),
        "--response", f"park-001={park}",
        "--response", f"travel-001={travel}",
        "--output", str(results / "predictions" / "openai-gpt-transcribe-001" / "run.json"),
        "--experiment-id", "openai-gpt-transcribe-001",
        "--model", "gpt-transcribe",
        "--prompt-version", "manual-mixed-v1",
        "--prompt-sha256", f"travel-001={'a' * 64}",
    ]


def test_import_keeps_raw_and_gold_separate_and_latency_unknown(tmp_path: Path) -> None:
    manifest, results, park, travel = _private_inputs(tmp_path)
    original_manifest = manifest.read_bytes()
    original_raw = (park.read_bytes(), travel.read_bytes())

    assert main(_import_args(manifest, results, park, travel)) == 0

    run_path = results / "predictions" / "openai-gpt-transcribe-001" / "run.json"
    run = TranscriptionRun.model_validate_json(run_path.read_text(encoding="utf-8"))
    assert run.model == "openai/gpt-transcribe"
    assert run.observations[0].transcript == "Um, I I went to the park."
    assert run.observations[0].latency_ms is None
    assert run.observations[0].usage is None
    assert run.observations[0].raw_response_sha256 == hashlib.sha256(original_raw[0]).hexdigest()
    assert run.observations[0].raw_response_path.endswith("/raw/park-001.json")
    assert run.observations[1].prompt_sha256 == "a" * 64
    assert manifest.read_bytes() == original_manifest
    assert (park.read_bytes(), travel.read_bytes()) == original_raw


def test_imported_prediction_can_be_reevaluated_without_stt(tmp_path: Path) -> None:
    manifest, results, park, travel = _private_inputs(tmp_path)
    assert main(_import_args(manifest, results, park, travel)) == 0
    run_path = results / "predictions" / "openai-gpt-transcribe-001" / "run.json"
    for evaluation_id in ("openai-evaluation-001", "openai-evaluation-002"):
        assert main(
            [
                "evaluate-engines",
                "--manifest", str(manifest),
                "--run", str(run_path),
                "--output-dir", str(results),
                "--evaluation-run-id", evaluation_id,
                "--evaluators", "custom",
            ]
        ) == 0
        index = json.loads((results / evaluation_id / "index.json").read_text())
        assert all(item["status"] == "success" for item in index["executions"])
        native = json.loads(
            (results / evaluation_id / "raw" / "park-001" / "custom.json").read_text()
        )
        assert native["latencyP50Ms"] is None
        assert native["samples"][0]["latencyMs"] is None


def test_import_rejects_response_outside_private_results(tmp_path: Path) -> None:
    manifest, results, park, travel = _private_inputs(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_bytes(park.read_bytes())
    args = _import_args(manifest, results, outside, travel)
    with pytest.raises(SystemExit) as exit_info:
        main(args)
    assert exit_info.value.code == 2
    assert not (results / "predictions" / "openai-gpt-transcribe-001" / "run.json").exists()
