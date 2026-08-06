import asyncio

import pytest

from app.config import Settings
from app.evaluation_cache import EvaluationCache
from app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationV2Response,
    HigherAnswerRequest,
    HigherAnswerResponse,
)
from app.services.evaluation_service import EvaluationService
from app.services.evaluation_v2_service import EvaluationV2Service, HigherAnswerService
from tests.helpers import evaluation_output, evaluation_request


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


def test_evaluation_cache_key_never_depends_on_usage_logging() -> None:
    request = EvaluationRequest.model_validate(evaluation_request())
    cache = EvaluationCache[EvaluationResponse](ttl_seconds=300, max_entries=8)
    first = EvaluationService(
        object(),
        "prompt",
        Settings(_env_file=None, usage_log_enabled=False),
        cache,
    )
    second = EvaluationService(
        object(),
        "prompt",
        Settings(_env_file=None, usage_log_enabled=True),
        cache,
    )

    assert first._cache_key(request) == second._cache_key(request)


def test_v2_result_and_stable_prompt_keys_exclude_dynamic_suffix() -> None:
    request = EvaluationRequest.model_validate(evaluation_request())
    changed_payload = evaluation_request()
    changed_payload["transcript"] = "A different learner transcript."
    changed = EvaluationRequest.model_validate(changed_payload)
    first = EvaluationV2Service(
        object(),
        "stable prompt",
        Settings(_env_file=None, usage_log_enabled=False),
        EvaluationCache[EvaluationV2Response](ttl_seconds=300, max_entries=8),
    )
    second = EvaluationV2Service(
        object(),
        "stable prompt",
        Settings(_env_file=None, usage_log_enabled=True),
        EvaluationCache[EvaluationV2Response](ttl_seconds=300, max_entries=8),
    )

    assert first._cache_key(request) == second._cache_key(request)
    assert first._cache_key(request) != first._cache_key(changed)
    assert first._prompt_cache_key() == second._prompt_cache_key()
    assert request.transcript not in first._prompt_cache_key()


def test_higher_answer_cache_key_excludes_dynamic_transcript() -> None:
    source = evaluation_request()
    request = HigherAnswerRequest.model_validate(
        {
            "profile": {
                "targetLevel": source["profile"]["targetLevel"],
                "currentLevel": source["profile"]["currentLevel"],
            },
            "question": {
                "type": source["question"]["type"],
                "topic": source["question"]["topic"],
                "question": source["question"]["question"],
            },
            "transcript": source["transcript"],
            "mostLikelyLevel": "IM2",
            "baseAnswer": evaluation_output().base_answer,
        }
    )
    first = HigherAnswerService(
        object(),
        "stable higher prompt",
        Settings(_env_file=None, usage_log_enabled=False),
        EvaluationCache[HigherAnswerResponse](ttl_seconds=300, max_entries=8),
    )
    second = HigherAnswerService(
        object(),
        "stable higher prompt",
        Settings(_env_file=None, usage_log_enabled=True),
        EvaluationCache[HigherAnswerResponse](ttl_seconds=300, max_entries=8),
    )

    assert first._cache_key(request) == second._cache_key(request)
    assert first._prompt_cache_key() == second._prompt_cache_key()
    assert request.transcript not in first._prompt_cache_key()
