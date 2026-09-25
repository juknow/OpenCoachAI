import json
from pathlib import Path

from app.stt_benchmark.__main__ import main
from app.stt_benchmark.evaluation_engine import evaluate_transcription_run

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = BACKEND_DIR / "evals" / "transcription"


def test_new_evaluate_command_uses_central_engine(capsys) -> None:
    assert main(
        [
            "evaluate",
            "--manifest",
            str(EXAMPLE_DIR / "manifest.example.json"),
            "--run",
            str(EXAMPLE_DIR / "run.example.json"),
        ]
    ) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["datasetVersion"] == "stt-eval-v1"
    assert report["wordErrorRate"] == 0


def test_legacy_report_import_points_to_central_engine() -> None:
    from app.evals.transcription_report import evaluate_transcription_run as legacy_entry

    assert legacy_entry is evaluate_transcription_run


def test_evaluate_engines_cli_stores_metadata_and_custom_native_output(
    tmp_path: Path, capsys
) -> None:
    evaluation_dir = tmp_path / "transcription"
    results_dir = evaluation_dir / "results"
    evaluation_dir.mkdir()
    manifest = evaluation_dir / "manifest.json"
    run = evaluation_dir / "run.json"
    manifest.write_text((EXAMPLE_DIR / "manifest.example.json").read_text(), encoding="utf-8")
    run.write_text((EXAMPLE_DIR / "run.example.json").read_text(), encoding="utf-8")

    assert main(
        [
            "evaluate-engines",
            "--manifest",
            str(manifest),
            "--run",
            str(run),
            "--output-dir",
            str(results_dir),
            "--evaluation-run-id",
            "multi-engine-001",
            "--evaluators",
            "custom",
        ]
    ) == 0

    index_path = results_dir / "multi-engine-001" / "index.json"
    index = json.loads(index_path.read_text())
    assert len(index["executions"]) == 3
    assert all(item["status"] == "success" for item in index["executions"])
    assert all(item["evaluatorId"] == "custom" for item in index["executions"])
    assert "success=3" in capsys.readouterr().out
