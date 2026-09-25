"""Compatibility imports. Implementation lives in app.stt_benchmark."""

from app.stt_benchmark.contracts.run import (
    TranscriptionObservation,
    TranscriptionRun,
    TranscriptionRunConfig,
)

__all__ = ["TranscriptionRun", "TranscriptionRunConfig", "TranscriptionObservation"]
