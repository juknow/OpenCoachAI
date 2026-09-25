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
