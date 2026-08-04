import hashlib
import json
import re

from app.config import Settings
from app.errors import ProviderResponseError
from app.evaluation_cache import ResultCache
from app.evaluation_defaults import SAFETY_NOTICE, estimated_range_for, reusable_structure_for
from app.providers.base import EvaluationProvider
from app.schemas.common import ResponseMetadata
from app.schemas.evaluation import (
    CompactDimension,
    CompactEvaluationOutput,
    EvaluationModelOutput,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
)
from app.usage_telemetry import record_server_cache_event

WORD_PATTERN = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]+|[^.!?]+$")


def count_improvement_words(sentences: list[str]) -> int:
    return len(WORD_PATTERN.findall(" ".join(sentences)))


def count_improvement_sentences(sentences: list[str]) -> int:
    text = " ".join(sentences).strip()
    return len([match for match in SENTENCE_PATTERN.findall(text) if match.strip()])


def validate_improvement_sentences(
    sentences: list[str], *, minimum: int, maximum: int
) -> None:
    actual_count = count_improvement_sentences(sentences)
    every_item_is_one_sentence = all(
        count_improvement_sentences([sentence]) == 1
        and bool(re.search(r"[.!?][\"']?$", sentence.strip()))
        for sentence in sentences
    )
    if not every_item_is_one_sentence or not minimum <= actual_count <= maximum:
        raise ProviderResponseError("INVALID_IMPROVEMENT_ANSWER")


def dimension_payload(value: CompactDimension) -> dict[str, object]:
    return {"score": value.score, "reason": value.feedback}


def compact_to_public(
    output: CompactEvaluationOutput,
    request: EvaluationRequest,
) -> EvaluationModelOutput:
    delivery = output.delivery
    return EvaluationModelOutput.model_validate(
        {
            "mostLikelyLevel": output.level,
            "confidence": output.confidence,
            "confidenceReason": output.confidence_why,
            "summaryKorean": output.summary,
            "dimensions": {
                "taskCompletion": dimension_payload(output.dims.task),
                "contentSpecificity": dimension_payload(output.dims.content),
                "discourseOrganization": dimension_payload(output.dims.organization),
                "timeFrameControl": dimension_payload(output.dims.time_frames),
                "grammarControl": dimension_payload(output.dims.grammar),
                "vocabularyRange": dimension_payload(output.dims.vocabulary),
                "fluencyComprehensibility": dimension_payload(output.dims.fluency),
            },
            "conversationalDelivery": {
                "fluency": dimension_payload(delivery.fluency),
                "accuracy": dimension_payload(delivery.accuracy),
                "naturalness": dimension_payload(delivery.naturalness),
                "mainPoint": {
                    "status": delivery.main_point.status,
                    "first20SecondsEstimate": request.speech_metrics.opening_20_second_estimate,
                    "feedbackKorean": delivery.main_point.feedback,
                },
                "feelingLanguage": {
                    "expressions": delivery.feelings,
                    "feedbackKorean": "감정과 반응을 나타내는 표현을 확인했습니다.",
                },
                "discourseMarkers": {
                    "functional": delivery.markers.functional,
                    "disruptive": delivery.markers.disruptive,
                    "feedbackKorean": "연결 표현과 발화 흐름을 함께 확인했습니다.",
                },
            },
            "naturalPhraseSuggestions": [
                {
                    "contextKorean": item.context,
                    "phraseEnglish": item.phrase,
                    "usageKorean": item.usage,
                }
                for item in output.phrases
            ],
            "recommendedVocabulary": [
                {
                    "category": item.category,
                    "wordOrPhraseEnglish": item.phrase,
                    "meaningKorean": item.meaning,
                    "whyRecommendedKorean": item.why,
                    "exampleSentenceEnglish": item.example,
                }
                for item in output.vocab
            ],
            "strengths": [
                {
                    "title": item.title,
                    "explanationKorean": item.explanation,
                    "evidenceFromTranscript": item.evidence,
                }
                for item in output.strengths
            ],
            "limitations": [],
            "primaryLevelBlocker": {
                "title": output.blocker.title,
                "explanationKorean": output.blocker.explanation,
                "evidenceFromTranscript": output.blocker.evidence,
            },
            "corrections": [
                {
                    "original": item.original,
                    "corrected": item.corrected,
                    "explanationKorean": item.explanation,
                }
                for item in output.corrections
            ],
            "retryMission": output.missions,
            "recommendedNextQuestionType": output.next_question_type,
            "minimalCorrectionSentences": output.base_answer,
            "nextLevelSentences": output.higher_answer,
        }
    )


class EvaluationService:
    def __init__(
        self,
        provider: EvaluationProvider,
        prompt: str,
        settings: Settings,
        cache: ResultCache[EvaluationResponse],
    ) -> None:
        self._provider = provider
        self._prompt = prompt
        self._settings = settings
        self._cache = cache

    async def evaluate(self, request: EvaluationRequest, request_id: str) -> EvaluationResponse:
        cache_key = self._cache_key(request)
        response, cache_status = await self._cache.get_or_create(
            cache_key,
            lambda: self._evaluate_uncached(request, request_id),
        )
        record_server_cache_event(
            status=cache_status,
            enabled=self._settings.detailed_usage_logging_enabled,
        )
        return response.model_copy(
            deep=True,
            update={
                "metadata": ResponseMetadata(
                    request_id=request_id,
                    model=response.metadata.model,
                    usage=response.metadata.usage,
                )
            },
        )

    async def _evaluate_uncached(
        self,
        request: EvaluationRequest,
        request_id: str,
    ) -> EvaluationResponse:
        response_model = (
            EvaluationModelOutput
            if self._settings.evaluation_schema_version == "v1"
            else CompactEvaluationOutput
        )
        provider_result = await self._provider.evaluate(
            system_prompt=self._prompt,
            user_payload=self._ai_payload(request),
            response_model=response_model,
            request_type="evaluation_legacy",
            prompt_cache_key=self._prompt_cache_key(),
        )

        try:
            if self._settings.evaluation_schema_version == "v1":
                public_output = EvaluationModelOutput.model_validate(
                    provider_result.output.model_dump()
                )
            else:
                parsed = CompactEvaluationOutput.model_validate(provider_result.output.model_dump())
                public_output = compact_to_public(parsed, request)
            validate_improvement_sentences(
                public_output.minimal_correction_sentences,
                minimum=10,
                maximum=12,
            )
            validate_improvement_sentences(
                public_output.next_level_sentences,
                minimum=12,
                maximum=15,
            )
            evaluation = EvaluationResult(
                **public_output.model_dump(),
                estimated_range=estimated_range_for(public_output.most_likely_level),
                reusable_structure=reusable_structure_for(request.question.type),
                safety_notice_korean=SAFETY_NOTICE,
            )
            return EvaluationResponse(
                evaluation=EvaluationResult.model_validate(evaluation.model_dump()),
                metadata=ResponseMetadata(
                    request_id=request_id,
                    model=provider_result.model,
                    usage=provider_result.usage,
                ),
            )
        except ProviderResponseError:
            raise
        except (TypeError, ValueError) as error:
            raise ProviderResponseError("INVALID_EVALUATION_RESPONSE") from error

    def _cache_key(self, request: EvaluationRequest) -> str:
        material = {
            "model": self._settings.evaluation_model,
            "promptVersion": self._settings.evaluation_prompt_version,
            "schemaVersion": self._settings.evaluation_schema_version,
            "promptHash": hashlib.sha256(self._prompt.encode("utf-8")).hexdigest(),
            "request": request.model_dump(mode="json", by_alias=True),
        }
        canonical = json.dumps(
            material,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _prompt_cache_key(self) -> str:
        return (
            f"opic:evaluation-legacy:{self._settings.evaluation_model}:"
            f"{self._settings.evaluation_prompt_version}:"
            f"{self._settings.evaluation_schema_version}"
        )

    @staticmethod
    def _ai_payload(request: EvaluationRequest) -> dict[str, object]:
        acoustic = request.speech_metrics.acoustic
        previous = request.previous_attempt
        return {
            "profile": {
                "targetLevel": request.profile.target_level,
                "currentLevel": request.profile.current_level,
            },
            "question": {
                "type": request.question.type,
                "topic": request.question.topic,
                "question": request.question.question,
            },
            "attemptNumber": request.attempt_number,
            "transcript": request.transcript,
            "speech": {
                "durationSeconds": request.speech_metrics.duration_seconds,
                "wordsPerMinute": request.speech_metrics.words_per_minute,
                "fillerRatePer100Words": request.speech_metrics.filler_rate_per_100_words,
                "opening20SecondEstimate": request.speech_metrics.opening_20_second_estimate,
                "initialResponseDelaySeconds": acoustic.initial_response_delay_seconds,
                "hesitationPauseCount": acoustic.hesitation_pause_count,
                "longPauseCount": acoustic.long_pause_count,
                "silenceRatio": acoustic.silence_ratio,
                "energyVariationIndex": acoustic.energy_variation_index,
                "confidence": acoustic.confidence,
            },
            "previousAttempt": (
                {
                    "primaryBlocker": previous.primary_blocker,
                    "retryMission": previous.retry_mission,
                }
                if previous
                else None
            ),
        }
