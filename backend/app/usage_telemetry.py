import json
import logging
from collections import deque
from dataclasses import asdict, dataclass
from threading import Lock

from app.schemas.common import UsageMetadata

LOGGER = logging.getLogger("opic.usage")
_EVALUATION_TOTALS: deque[int] = deque(maxlen=100)
_EVALUATION_TOTALS_LOCK = Lock()


@dataclass(frozen=True)
class UsageEvent:
    request_type: str
    model: str
    latency_ms: int
    success: bool
    retry_count: int
    input_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    audio_seconds: float | None = None
    error_type: str | None = None


def record_usage_event(event: UsageEvent, *, enabled: bool) -> None:
    if not enabled:
        return
    payload = {key: value for key, value in asdict(event).items() if value is not None}
    if event.request_type == "evaluation" and event.success and event.total_tokens > 0:
        with _EVALUATION_TOTALS_LOCK:
            _EVALUATION_TOTALS.append(event.total_tokens)
            payload["rolling_total_tokens_average"] = round(
                sum(_EVALUATION_TOTALS) / len(_EVALUATION_TOTALS),
                1,
            )
            payload["rolling_sample_count"] = len(_EVALUATION_TOTALS)
    LOGGER.info("openai_usage %s", json.dumps(payload, separators=(",", ":"), sort_keys=True))


def usage_event(
    *,
    request_type: str,
    model: str,
    latency_ms: int,
    success: bool,
    retry_count: int,
    usage: UsageMetadata | None = None,
    audio_seconds: float | None = None,
    error_type: str | None = None,
) -> UsageEvent:
    return UsageEvent(
        request_type=request_type,
        model=model,
        latency_ms=max(0, latency_ms),
        success=success,
        retry_count=max(0, retry_count),
        input_tokens=usage.input_tokens if usage else 0,
        cached_tokens=usage.cached_input_tokens if usage else 0,
        cache_write_tokens=usage.cache_write_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
        reasoning_tokens=usage.reasoning_tokens if usage else 0,
        total_tokens=usage.total_tokens if usage else 0,
        audio_seconds=audio_seconds,
        error_type=error_type,
    )


def record_server_cache_event(*, status: str, enabled: bool) -> None:
    if enabled:
        LOGGER.info("evaluation_cache %s", json.dumps({"status": status}, separators=(",", ":")))
