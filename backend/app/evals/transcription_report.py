"""Compatibility imports. Implementation lives in app.stt_benchmark."""

from app.stt_benchmark.contracts.evaluation import (
    AggregateRetention,
    TranscriptionEvaluationReport,
    TranscriptionSampleScore,
)
from app.stt_benchmark.evaluation_engine import evaluate_transcription_run

__all__ = [
    "AggregateRetention",
    "TranscriptionSampleScore",
    "TranscriptionEvaluationReport",
    "evaluate_transcription_run",
]
