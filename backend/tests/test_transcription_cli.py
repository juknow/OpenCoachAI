import json
from pathlib import Path

from app.evals.transcription_cli import main

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = BACKEND_DIR / "evals" / "transcription"


def example_arguments() -> list[str]:
    return [
        "--manifest",
        str(EXAMPLE_DIR / "manifest.example.json"),
        "--run",
        str(EXAMPLE_DIR / "run.example.json"),
    ]


def test_cli_writes_camel_case_report_to_requested_path(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "report.json"

    exit_code = main([*example_arguments(), "--output", str(output_path)])
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["experimentId"] == "mini-prompt-v1"
    assert report["sampleCount"] == 3
    assert report["wordErrorRate"] == 0
    assert report["hallucinationSamples"] == 0
    assert report["unexpectedOutcomeSamples"] == 0


def test_cli_prints_report_when_output_is_omitted(capsys) -> None:
    exit_code = main(example_arguments())
    output = capsys.readouterr().out

    assert exit_code == 0
    assert json.loads(output)["datasetVersion"] == "stt-eval-v1"

