"""Research CLI. Only implemented commands are advertised."""

import argparse
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STT benchmark tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("evaluate", add_help=False, help="Score saved JSON without STT calls.")
    subparsers.add_parser(
        "evaluate-engines",
        add_help=False,
        help="Run independent evaluators and preserve their native outputs.",
    )
    subparsers.add_parser("transcribe", add_help=False, help="Validate or execute local STT.")
    arguments, remaining = parser.parse_known_args(argv)
    if arguments.command == "evaluate":
        from app.stt_benchmark.interfaces.cli.evaluate import main as evaluate

        return evaluate(remaining)
    if arguments.command == "evaluate-engines":
        from app.stt_benchmark.interfaces.cli.evaluate_engines import main as evaluate_engines

        return evaluate_engines(remaining)
    from app.stt_benchmark.interfaces.cli.transcribe import main as transcribe

    return transcribe(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
