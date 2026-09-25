"""Compatibility imports. Implementation lives in app.stt_benchmark."""

from app.stt_benchmark.interfaces.cli.evaluate import (
    build_parser,
    main,
)

__all__ = ["build_parser", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
