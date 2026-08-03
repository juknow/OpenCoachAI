import json
import logging
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from threading import Lock

from app.schemas.common import UsageMetadata

LOGGER = logging.getLogger("opic.usage")
_USAGE_TOTALS: defaultdict[str, deque[int]] = defaultdict(lambda: deque(maxlen=100))
_USAGE_TOTALS_LOCK = Lock()


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
    if event.request_type != "transcription" and event.success and event.total_tokens > 0:
        with _USAGE_TOTALS_LOCK:
            totals = _USAGE_TOTALS[event.request_type]
            totals.append(event.total_tokens)
            payload["rolling_total_tokens_average"] = round(
                sum(totals) / len(totals),
                1,
            )
            payload["rolling_sample_count"] = len(totals)
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


def record_server_cache_event(
    *,
    status: str,
    enabled: bool,
    request_type: str = "evaluation_legacy",
) -> None:
    if enabled:
        LOGGER.info(
            "result_cache %s",
            json.dumps(
                {"requestType": request_type, "status": status},
                separators=(",", ":"),
            ),
        )
