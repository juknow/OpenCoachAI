import asyncio

import pytest

from app.config import Settings
from app.evaluation_cache import EvaluationCache
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.services.evaluation_service import EvaluationService
from tests.helpers import evaluation_request


@pytest.mark.asyncio
async def test_concurrent_identical_evaluations_are_coalesced() -> None:
    cache = EvaluationCache[str](ttl_seconds=300, max_entries=8)
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return "evaluation"

    first = asyncio.create_task(cache.get_or_create("same-key", factory))
    await started.wait()
    duplicate = asyncio.create_task(cache.get_or_create("same-key", factory))
    await asyncio.sleep(0)
    release.set()

    first_result, duplicate_result = await asyncio.gather(first, duplicate)
    cached_result = await cache.get_or_create("same-key", factory)

    assert calls == 1
    assert {first_result[1], duplicate_result[1]} == {"miss", "coalesced"}
    assert first_result[0] == duplicate_result[0] == "evaluation"
    assert cached_result == ("evaluation", "hit")


@pytest.mark.asyncio
async def test_failed_evaluation_is_not_cached() -> None:
    cache = EvaluationCache[str](ttl_seconds=300, max_entries=8)
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("expected")
        return "recovered"

    with pytest.raises(RuntimeError, match="expected"):
        await cache.get_or_create("same-key", factory)

    assert await cache.get_or_create("same-key", factory) == ("recovered", "miss")
    assert calls == 2


def test_evaluation_cache_key_never_depends_on_api_key() -> None:
    request = EvaluationRequest.model_validate(evaluation_request())
    cache = EvaluationCache[EvaluationResponse](ttl_seconds=300, max_entries=8)
    first = EvaluationService(
        object(),
        "prompt",
        Settings(_env_file=None, openai_api_key="first-private-key"),
        cache,
    )
    second = EvaluationService(
        object(),
        "prompt",
        Settings(_env_file=None, openai_api_key="different-private-key"),
        cache,
    )

    assert first._cache_key(request) == second._cache_key(request)
