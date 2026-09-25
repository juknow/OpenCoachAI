"""Compatibility imports. Implementation lives in app.stt_benchmark."""

from app.stt_benchmark.interfaces.cli.transcribe import (
    build_parser,
    main,
)
from app.stt_benchmark.transcription_runner import execute_dataset

__all__ = ["build_parser", "main", "execute_dataset"]

if __name__ == "__main__":
    raise SystemExit(main())
