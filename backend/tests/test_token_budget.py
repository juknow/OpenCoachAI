import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas.evaluation import (
    CompactEvaluationOutput,
    CompactEvaluationV2Output,
    CompactHigherAnswerOutput,
    EvaluationModelOutput,
    EvaluationRequest,
)
from app.services.evaluation_service import EvaluationService
from app.services.evaluation_v2_service import EvaluationV2Service
from tests.helpers import (
    evaluation_output,
    evaluation_request,
    evaluation_v2_output,
    higher_answer_output,
)

PROMPT_PATH = Path(__file__).resolve().parents[1] / "app" / "prompts" / "evaluation.txt"
CORE_PROMPT_PATH = Path(__file__).resolve().parents[1] / "app" / "prompts" / "evaluation_core.txt"
HIGHER_PROMPT_PATH = Path(__file__).resolve().parents[1] / "app" / "prompts" / "higher_answer.txt"


def estimate_tokens_offline(value: str) -> int:
    # Conservative regression heuristic only. Real usage.total_tokens remains the source of truth.
    weighted = sum(1 / 3.5 if ord(character) < 128 else 1 / 1.2 for character in value)
    return math.ceil(weighted)


def compact_json_schema() -> str:
    return json.dumps(
        CompactEvaluationOutput.model_json_schema(by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def test_compact_schema_and_payload_are_smaller_than_public_contract() -> None:
    request = EvaluationRequest.model_validate(evaluation_request())
    compact_payload = json.dumps(
        EvaluationService._ai_payload(request),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    public_payload = request.model_dump_json(by_alias=True)
    public_schema = json.dumps(
        EvaluationModelOutput.model_json_schema(by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    assert len(compact_payload) < len(public_payload) * 0.7
    assert len(compact_json_schema()) < len(public_schema)


def test_fixture_stays_within_offline_four_thousand_token_budget() -> None:
    request = EvaluationRequest.model_validate(evaluation_request())
    parts = [
        PROMPT_PATH.read_text(encoding="utf-8").strip(),
        compact_json_schema(),
        json.dumps(
            EvaluationService._ai_payload(request),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        evaluation_output().model_dump_json(by_alias=True),
    ]

    estimated_total = sum(estimate_tokens_offline(part) for part in parts)

    assert estimated_total <= 4_000


def test_v2_initial_evaluation_is_smaller_than_eager_contract() -> None:
    request = EvaluationRequest.model_validate(evaluation_request())
    payload = json.dumps(
        EvaluationV2Service._ai_payload(request),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    eager_parts = [
        PROMPT_PATH.read_text(encoding="utf-8").strip(),
        compact_json_schema(),
        payload,
        evaluation_output().model_dump_json(by_alias=True),
    ]
    lazy_parts = [
        CORE_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        json.dumps(
            CompactEvaluationV2Output.model_json_schema(by_alias=True),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        payload,
        evaluation_v2_output().model_dump_json(by_alias=True),
    ]
    eager_total = sum(estimate_tokens_offline(part) for part in eager_parts)
    lazy_total = sum(estimate_tokens_offline(part) for part in lazy_parts)

    assert lazy_total < eager_total
    assert lazy_total <= 3_600


def test_local_evaluation_fixture_fits_configured_context_budget() -> None:
    settings = Settings(_env_file=None, ollama_context_length=4096)
    request = EvaluationRequest.model_validate(evaluation_request())
    parts = [
        CORE_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        json.dumps(
            CompactEvaluationV2Output.model_json_schema(by_alias=True),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        json.dumps(
            EvaluationV2Service._ai_payload(request),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        evaluation_v2_output().model_dump_json(by_alias=True),
    ]
    estimated_total = sum(estimate_tokens_offline(part) for part in parts)

    assert estimated_total <= settings.ollama_context_length


def test_two_minute_answer_has_room_for_full_configured_output() -> None:
    long_transcript = " ".join(
        [
            (
                "Um, last weekend I went to a neighborhood park with my close friend, "
                "and we walked around the lake while talking about school and our plans."
            )
        ]
        * 14
    )
    payload = evaluation_request()
    payload["transcript"] = long_transcript
    payload["speechMetrics"]["durationSeconds"] = 120
    payload["speechMetrics"]["wordCount"] = len(long_transcript.split())
    payload["speechMetrics"]["wordsPerMinute"] = round(len(long_transcript.split()) / 2)
    payload["speechMetrics"]["opening20SecondEstimate"] = long_transcript[:500]
    request = EvaluationRequest.model_validate(payload)
    settings = Settings(_env_file=None)
    input_parts = [
        CORE_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        json.dumps(
            CompactEvaluationV2Output.model_json_schema(by_alias=True),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        json.dumps(
            EvaluationV2Service._ai_payload(request),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    ]
    required_context = sum(estimate_tokens_offline(part) for part in input_parts)
    required_context += settings.evaluation_max_output_tokens

    assert required_context > 4_096
    assert required_context <= settings.ollama_context_length


def test_explicit_cache_breakpoint_has_an_eligible_stable_prefix() -> None:
    stable_prefix = [
        CORE_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        json.dumps(
            CompactEvaluationV2Output.model_json_schema(by_alias=True),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    ]

    assert sum(estimate_tokens_offline(part) for part in stable_prefix) >= 1_024


def test_transport_schema_omits_string_lengths_but_server_still_validates() -> None:
    schema_json = json.dumps(
        CompactEvaluationV2Output.model_json_schema(by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert '"minLength"' not in schema_json
    assert '"maxLength"' not in schema_json
    assert '"minItems":10' in schema_json
    assert '"maxItems":12' in schema_json

    invalid_output = evaluation_v2_output().model_dump()
    invalid_output["summary"] = ""
    with pytest.raises(ValidationError):
        CompactEvaluationV2Output.model_validate(invalid_output)


def test_lazy_higher_answer_has_a_separate_bounded_budget() -> None:
    request = evaluation_request()
    higher_payload = {
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
        "baseAnswer": evaluation_output().base_answer,
    }
    parts = [
        HIGHER_PROMPT_PATH.read_text(encoding="utf-8").strip(),
        json.dumps(
            CompactHigherAnswerOutput.model_json_schema(by_alias=True),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        json.dumps(higher_payload, ensure_ascii=False, separators=(",", ":")),
        higher_answer_output().model_dump_json(by_alias=True),
    ]

    estimated_total = sum(estimate_tokens_offline(part) for part in parts)

    assert estimated_total <= 1_800
