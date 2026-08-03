from fastapi.testclient import TestClient

from tests.conftest import FakeProvider
from tests.helpers import evaluation_request


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
    }
    call = fake_provider.evaluation_calls[0]
    assert call["response_model"].__name__ == "EvaluationModelOutput"
    assert call["user_payload"]["transcript"].startswith("Um,")


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
