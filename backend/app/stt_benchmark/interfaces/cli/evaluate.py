import argparse
from collections.abc import Sequence
from pathlib import Path

from app.stt_benchmark.contracts.dataset import TranscriptionDataset
from app.stt_benchmark.contracts.run import TranscriptionRun
from app.stt_benchmark.evaluation_engine import evaluate_transcription_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an offline STT quality report from a manifest and saved run.",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    dataset = TranscriptionDataset.model_validate_json(
        arguments.manifest.read_text(encoding="utf-8")
    )
    run = TranscriptionRun.model_validate_json(arguments.run.read_text(encoding="utf-8"))
    report = evaluate_transcription_run(dataset, run)
    report_json = report.model_dump_json(by_alias=True, indent=2) + "\n"

    if arguments.output is None:
        print(report_json, end="")
        return 0

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(report_json, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
