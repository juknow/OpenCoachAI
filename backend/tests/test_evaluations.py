import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import ProviderResponseError
from app.evaluation_cache import EvaluationCache
from app.providers.base import ProviderEvaluation
from app.schemas.common import UsageMetadata
from app.schemas.evaluation import (
    EvaluationModelOutput,
    EvaluationRequest,
    EvaluationResponse,
)
from app.services.evaluation_service import (
    EvaluationService,
    compact_to_public,
    count_improvement_sentences,
    count_improvement_words,
    normalize_improvement_sentences,
)
from tests.conftest import FakeProvider
from tests.helpers import evaluation_output, evaluation_request


def test_evaluation_returns_enriched_structured_result(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    response = client.post("/api/evaluations", json=evaluation_request())
    assert response.status_code == 200
    payload = response.json()
    evaluation = payload["evaluation"]
    assert evaluation["mostLikelyLevel"] == "IM2"
    assert evaluation["estimatedRange"] == {"lower": "IM1", "upper": "IM3"}
    assert len(evaluation["minimalCorrectionSentences"]) == 10
    assert len(evaluation["nextLevelSentences"]) == 13
    assert len(evaluation["retryMission"]) == 3
    assert "공식 OPIc 점수가 아닙니다" in evaluation["safetyNoticeKorean"]
    assert payload["metadata"]["usage"] == {
        "inputTokens": 120,
        "outputTokens": 340,
        "cachedInputTokens": 20,
        "cacheWriteTokens": 10,
        "reasoningTokens": 0,
        "totalTokens": 460,
    }
    call = fake_provider.evaluation_calls[0]
    assert call["response_model"].__name__ == "CompactEvaluationOutput"
    assert call["user_payload"]["transcript"].startswith("Um,")
    assert set(call["user_payload"]["profile"]) == {"targetLevel", "currentLevel"}
    assert "koreanTranslation" not in call["user_payload"]["question"]
    assert evaluation["limitations"] == []
    assert evaluation["conversationalDelivery"]["mainPoint"]["first20SecondsEstimate"].startswith(
        "Um,"
    )
    base = evaluation["minimalCorrectionSentences"]
    higher = evaluation["nextLevelSentences"]
    assert count_improvement_sentences(base) == 10
    assert 120 <= count_improvement_words(base) <= 160
    assert count_improvement_sentences(higher) == 13
    assert 140 <= count_improvement_words(higher) <= 180


def test_v2_evaluation_uses_slim_lazy_contract(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    response = client.post("/api/v2/evaluations", json=evaluation_request())

    assert response.status_code == 200
    payload = response.json()
    evaluation = payload["evaluation"]
    assert set(evaluation) == {
        "mostLikelyLevel",
        "estimatedRange",
        "confidence",
        "confidenceReason",
        "summaryKorean",
        "dimensions",
        "conversationalDelivery",
        "naturalPhraseSuggestions",
        "recommendedVocabulary",
        "strengths",
        "primaryLevelBlocker",
        "corrections",
        "retryMission",
        "baseAnswer",
        "reusableStructure",
        "safetyNoticeKorean",
    }
    assert evaluation["mostLikelyLevel"] == "IM2"
    assert evaluation["baseAnswer"]["variant"] == "core"
    assert evaluation["baseAnswer"]["sentenceCount"] == 10
    assert 120 <= evaluation["baseAnswer"]["wordCount"] <= 160
    assert "nextLevelSentences" not in evaluation
    assert "limitations" not in evaluation
    assert "recommendedNextQuestionType" not in evaluation
    assert "first20SecondsEstimate" not in evaluation["conversationalDelivery"]["mainPoint"]
    assert set(evaluation["conversationalDelivery"]) == {
        "fluency",
        "accuracy",
        "naturalness",
        "mainPoint",
        "feelingExpressions",
        "functionalMarkers",
        "disruptiveMarkers",
    }
    call = fake_provider.evaluation_calls[0]
    assert call["response_model"].__name__ == "CompactEvaluationV2Output"
    assert call["request_type"] == "evaluation_v2"
    assert call["prompt_cache_key"].startswith("opic:evaluation-v2:")


def test_higher_answer_is_generated_lazily_and_reused(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    request = evaluation_request()
    base_answer = evaluation_output().base_answer
    payload = {
        "profile": {
            "targetLevel": request["profile"]["targetLevel"],
            "currentLevel": request["profile"]["currentLevel"],
        },
        "question": {
            "type": request["question"]["type"],
            "topic": request["question"]["topic"],
            "question": request["question"]["question"],
        },
        "transcript": request["transcript"],
        "mostLikelyLevel": "IM2",
        "baseAnswer": base_answer,
    }

    first = client.post("/api/v2/improvements/higher", json=payload)
    second = client.post("/api/v2/improvements/higher", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["answer"]["variant"] == "next"
    assert first.json()["answer"]["sentenceCount"] == 13
    assert 140 <= first.json()["answer"]["wordCount"] <= 180
    assert first.json()["answer"] == second.json()["answer"]
    assert first.json()["metadata"]["requestId"] != second.json()["metadata"]["requestId"]
    assert len(fake_provider.evaluation_calls) == 1
    call = fake_provider.evaluation_calls[0]
    assert call["request_type"] == "higher_answer"
    assert call["max_output_tokens"] == 900
    assert call["prompt_cache_key"].startswith("opic:higher-answer:")


def test_evaluation_rejects_invalid_cardinality(client: TestClient) -> None:
    request = evaluation_request()
    request["previousAttempt"] = {
        "level": "IM1",
        "dimensionScores": {
            "taskCompletion": 2,
            "contentSpecificity": 2,
            "discourseOrganization": 2,
            "timeFrameControl": 2,
            "grammarControl": 2,
            "vocabularyRange": 2,
            "fluencyComprehensibility": 2,
        },
        "primaryBlocker": "detail",
        "retryMission": ["only one"],
    }
    response = client.post("/api/evaluations", json=request)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_identical_evaluation_is_reused_from_memory_cache(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    first = client.post("/api/evaluations", json=evaluation_request())
    second = client.post("/api/evaluations", json=evaluation_request())

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(fake_provider.evaluation_calls) == 1
    assert first.json()["evaluation"] == second.json()["evaluation"]
    assert first.json()["metadata"]["requestId"] != second.json()["metadata"]["requestId"]


def test_truncated_output_uses_specific_api_error_contract(
    client: TestClient, fake_provider: FakeProvider
) -> None:
    fake_provider.evaluation_error = ProviderResponseError("EVALUATION_OUTPUT_TRUNCATED")

    response = client.post("/api/evaluations", json=evaluation_request())

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_OUTPUT_TRUNCATED"
    assert len(fake_provider.evaluation_calls) == 1


def test_improvement_answer_minor_format_errors_are_normalized() -> None:
    sentences = evaluation_output().base_answer
    malformed = [
        f"{sentences[0]} {sentences[1]}",
        *sentences[2:-1],
        sentences[-1].removesuffix("."),
    ]

    normalized = normalize_improvement_sentences(malformed, minimum=10, maximum=12)

    assert len(normalized) == 10
    assert normalized[-1].endswith(".")
    assert count_improvement_sentences(normalized) == 10


@pytest.mark.asyncio
async def test_v1_schema_fallback_preserves_public_evaluation_contract() -> None:
    request = EvaluationRequest.model_validate(evaluation_request())
    public_output = compact_to_public(evaluation_output(), request)

    class V1Provider:
        async def evaluate(self, **kwargs) -> ProviderEvaluation:
            assert kwargs["response_model"] is EvaluationModelOutput
            return ProviderEvaluation(
                output=public_output,
                model="qwen3:4b",
                usage=UsageMetadata(input_tokens=1, output_tokens=1, total_tokens=2),
            )

    service = EvaluationService(
        V1Provider(),
        "v1 prompt",
        Settings(
            _env_file=None,
            evaluation_schema_version="v1",
        ),
        EvaluationCache[EvaluationResponse](ttl_seconds=0, max_entries=1),
    )

    response = await service.evaluate(request, "request-id")

    assert response.evaluation.most_likely_level == public_output.most_likely_level
    assert len(response.evaluation.minimal_correction_sentences) == 10
