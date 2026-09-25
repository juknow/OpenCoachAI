import asyncio
import importlib.util
import json
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from app.stt_benchmark.contracts.evaluator import EvaluatorInput, TranscriptSegment
from app.stt_benchmark.evaluators.contract import (
    EvaluatorFailure,
    NativeEvaluatorOutput,
    SupportDecision,
)


def _native_error_rate(value: object) -> dict[str, object]:
    if is_dataclass(value):
        return asdict(value)
    result: dict[str, object] = {}
    for name in (
        "error_rate",
        "errors",
        "length",
        "insertions",
        "deletions",
        "substitutions",
        "missed_speaker",
        "falarm_speaker",
        "scored_speaker",
        "assignment",
    ):
        if hasattr(value, name):
            raw = getattr(value, name)
            if isinstance(raw, tuple):
                raw = [list(item) if isinstance(item, tuple) else item for item in raw]
            result[name] = raw
    return result


def _speaker_text(segments: tuple[TranscriptSegment, ...]) -> list[str]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for segment in segments:
        grouped[segment.speaker or "speaker-unknown"].append(segment.words)
    return [" ".join(words) for _, words in sorted(grouped.items())]


def _segment_dicts(segments: tuple[TranscriptSegment, ...]) -> list[dict[str, Any]]:
    return [
        {
            "words": segment.words,
            "speaker": segment.speaker,
            "start_time": segment.start_time,
            "end_time": segment.end_time,
        }
        for segment in segments
    ]


class MeetEvalEvaluator:
    evaluator_id = "meeteval"
    normalization_profile = "meeteval-native-v1"
    required_inputs = frozenset({"gold_text", "prediction_text"})
    supported_metrics = frozenset({"siso_wer", "cpwer", "tcpwer"})

    def __init__(self, collar_seconds: float = 5.0) -> None:
        if collar_seconds < 0:
            raise ValueError("MeetEval collar must not be negative")
        self.collar_seconds = collar_seconds
        try:
            self.evaluator_version = version("meeteval")
        except PackageNotFoundError:
            self.evaluator_version = "not-installed"

    def supports(self, evaluator_input: EvaluatorInput) -> SupportDecision:
        if (evaluator_input.reference_segments is None) != (
            evaluator_input.prediction_segments is None
        ):
            return SupportDecision.no("both_reference_and_prediction_segments_required")
        segments = (
            (*evaluator_input.reference_segments, *evaluator_input.prediction_segments)
            if evaluator_input.reference_segments is not None
            and evaluator_input.prediction_segments is not None
            else ()
        )
        if segments and any(segment.speaker is None for segment in segments):
            return SupportDecision.no("meeteval_segments_require_speaker_labels")
        has_any_time = any(segment.start_time is not None for segment in segments)
        has_all_times = all(segment.start_time is not None for segment in segments)
        if has_any_time and not has_all_times:
            return SupportDecision.no("meeteval_segments_have_incomplete_timestamps")
        if importlib.util.find_spec("meeteval") is None:
            return SupportDecision.no("dependency_not_installed:meeteval")
        return SupportDecision.yes()

    async def evaluate(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        return await asyncio.to_thread(self._evaluate_sync, evaluator_input)

    def _evaluate_sync(self, evaluator_input: EvaluatorInput) -> NativeEvaluatorOutput:
        try:
            import meeteval

            reference_segments = evaluator_input.reference_segments
            prediction_segments = evaluator_input.prediction_segments
            if reference_segments is None or prediction_segments is None:
                native = meeteval.wer.wer.siso.siso_word_error_rate(
                    evaluator_input.gold_text,
                    evaluator_input.prediction_text,
                )
                mode = "siso_wer"
            else:
                has_times = all(
                    segment.start_time is not None and segment.end_time is not None
                    for segment in (*reference_segments, *prediction_segments)
                )
                if has_times:
                    native = meeteval.wer.wer.time_constrained.tcp_word_error_rate(
                        _segment_dicts(reference_segments),
                        _segment_dicts(prediction_segments),
                        collar=self.collar_seconds,
                    )
                    mode = "tcpwer"
                else:
                    native = meeteval.wer.wer.cp.cp_word_error_rate(
                        _speaker_text(reference_segments),
                        _speaker_text(prediction_segments),
                    )
                    mode = "cpwer"
        except Exception as error:
            raise EvaluatorFailure(f"meeteval_execution_failed:{type(error).__name__}") from error
        payload = json.dumps(
            {"mode": mode, "result": _native_error_rate(native)},
            ensure_ascii=False,
            indent=2,
            default=str,
        ).encode("utf-8")
        return NativeEvaluatorOutput(payload=payload, suffix=".json", media_type="application/json")
