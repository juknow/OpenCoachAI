import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import Literal

CacheStatus = Literal["miss", "hit", "coalesced", "disabled"]


@dataclass(frozen=True)
class CacheEntry[ValueT]:
    expires_at: float
    value: ValueT


class EvaluationCache[ValueT]:
    def __init__(self, *, ttl_seconds: int, max_entries: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: OrderedDict[str, CacheEntry[ValueT]] = OrderedDict()
        self._inflight: dict[str, asyncio.Task[ValueT]] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        key: str,
        factory: Callable[[], Awaitable[ValueT]],
    ) -> tuple[ValueT, CacheStatus]:
        if self._ttl_seconds == 0:
            return await factory(), "disabled"

        async with self._lock:
            now = monotonic()
            self._purge_expired(now)
            cached = self._entries.get(key)
            if cached is not None:
                self._entries.move_to_end(key)
                return cached.value, "hit"

            task = self._inflight.get(key)
            if task is not None:
                status: CacheStatus = "coalesced"
            else:
                task = asyncio.create_task(self._run_and_store(key, factory))
                self._inflight[key] = task
                status = "miss"

        return await asyncio.shield(task), status

    async def _run_and_store(
        self,
        key: str,
        factory: Callable[[], Awaitable[ValueT]],
    ) -> ValueT:
        try:
            value = await factory()
            async with self._lock:
                self._entries[key] = CacheEntry(
                    expires_at=monotonic() + self._ttl_seconds,
                    value=value,
                )
                self._entries.move_to_end(key)
                while len(self._entries) > self._max_entries:
                    self._entries.popitem(last=False)
            return value
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

    def _purge_expired(self, now: float) -> None:
        expired = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in expired:
            self._entries.pop(key, None)
