import hashlib
import json

from app.config import Settings
from app.errors import ProviderResponseError
from app.evaluation_cache import ResultCache
from app.evaluation_defaults import SAFETY_NOTICE, estimated_range_for, reusable_structure_for
from app.providers.base import EvaluationProvider
from app.schemas.common import ResponseMetadata
from app.schemas.evaluation import (
    CompactDimension,
    CompactEvaluationV2Output,
    CompactEvidence,
    CompactHigherAnswerOutput,
    EvaluationRequest,
    EvaluationV2Response,
    EvaluationV2Result,
    HigherAnswerRequest,
    HigherAnswerResponse,
    ImprovementAnswerResult,
)
from app.services.evaluation_service import (
    EvaluationService,
    count_improvement_sentences,
    count_improvement_words,
    validate_improvement_sentences,
)
from app.usage_telemetry import record_server_cache_event


def _dimension(value: CompactDimension) -> dict[str, object]:
    return {"score": value.score, "reason": value.feedback}


def _evidence(value: CompactEvidence) -> dict[str, object]:
    return {
        "title": value.title,
        "explanationKorean": value.explanation,
        "evidenceFromTranscript": value.evidence,
    }


def _answer(sentences: list[str], variant: str) -> ImprovementAnswerResult:
    return ImprovementAnswerResult.model_validate(
        {
            "variant": variant,
            "sentences": sentences,
            "sentenceCount": count_improvement_sentences(sentences),
            "wordCount": count_improvement_words(sentences),
        }
    )


def compact_to_v2(
    output: CompactEvaluationV2Output,
    request: EvaluationRequest,
) -> EvaluationV2Result:
    delivery = output.delivery
    return EvaluationV2Result.model_validate(
        {
            "mostLikelyLevel": output.level,
            "estimatedRange": estimated_range_for(output.level),
            "confidence": output.confidence,
            "confidenceReason": output.confidence_why,
            "summaryKorean": output.summary,
            "dimensions": {
                "taskCompletion": _dimension(output.dims.task),
                "contentSpecificity": _dimension(output.dims.content),
                "discourseOrganization": _dimension(output.dims.organization),
                "timeFrameControl": _dimension(output.dims.time_frames),
                "grammarControl": _dimension(output.dims.grammar),
                "vocabularyRange": _dimension(output.dims.vocabulary),
                "fluencyComprehensibility": _dimension(output.dims.fluency),
            },
            "conversationalDelivery": {
                "fluency": _dimension(delivery.fluency),
                "accuracy": _dimension(delivery.accuracy),
                "naturalness": _dimension(delivery.naturalness),
                "mainPoint": {
                    "status": delivery.main_point.status,
                    "feedbackKorean": delivery.main_point.feedback,
                },
                "feelingExpressions": delivery.feelings,
                "functionalMarkers": delivery.markers.functional,
                "disruptiveMarkers": delivery.markers.disruptive,
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
            "strengths": [_evidence(item) for item in output.strengths],
            "primaryLevelBlocker": _evidence(output.blocker),
            "corrections": [
                {
                    "original": item.original,
                    "corrected": item.corrected,
                    "explanationKorean": item.explanation,
                }
                for item in output.corrections
            ],
            "retryMission": output.missions,
            "baseAnswer": _answer(output.base_answer, "core"),
            "reusableStructure": reusable_structure_for(request.question.type),
            "safetyNoticeKorean": SAFETY_NOTICE,
        }
    )


class EvaluationV2Service:
    def __init__(
        self,
        provider: EvaluationProvider,
        prompt: str,
        settings: Settings,
        cache: ResultCache[EvaluationV2Response],
    ) -> None:
        self._provider = provider
        self._prompt = prompt
        self._settings = settings
        self._cache = cache

    async def evaluate(
        self,
        request: EvaluationRequest,
        request_id: str,
    ) -> EvaluationV2Response:
        response, cache_status = await self._cache.get_or_create(
            self._cache_key(request),
            lambda: self._evaluate_uncached(request, request_id),
        )
        record_server_cache_event(
            status=cache_status,
            enabled=self._settings.detailed_usage_logging_enabled,
            request_type="evaluation_v2",
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
    ) -> EvaluationV2Response:
        provider_result = await self._provider.evaluate(
            system_prompt=self._prompt,
            user_payload=self._ai_payload(request),
            response_model=CompactEvaluationV2Output,
            request_type="evaluation_v2",
            prompt_cache_key=self._prompt_cache_key(),
        )
        try:
            output = CompactEvaluationV2Output.model_validate(
                provider_result.output.model_dump()
            )
            validate_improvement_sentences(output.base_answer, minimum=10, maximum=12)
            return EvaluationV2Response(
                evaluation=compact_to_v2(output, request),
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
        return self._hash(
            {
                "kind": "evaluation-v2",
                "model": self._settings.evaluation_model,
                "promptVersion": self._settings.evaluation_v2_prompt_version,
                "schemaVersion": self._settings.evaluation_v2_schema_version,
                "promptHash": hashlib.sha256(self._prompt.encode("utf-8")).hexdigest(),
                "request": request.model_dump(mode="json", by_alias=True),
            }
        )

    def _prompt_cache_key(self) -> str:
        return (
            f"opic:evaluation-v2:{self._settings.evaluation_model}:"
            f"{self._settings.evaluation_v2_prompt_version}:"
            f"{self._settings.evaluation_v2_schema_version}"
        )

    @staticmethod
    def _ai_payload(request: EvaluationRequest) -> dict[str, object]:
        return EvaluationService._ai_payload(request)

    @staticmethod
    def _hash(material: dict[str, object]) -> str:
        canonical = json.dumps(
            material,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class HigherAnswerService:
    def __init__(
        self,
        provider: EvaluationProvider,
        prompt: str,
        settings: Settings,
        cache: ResultCache[HigherAnswerResponse],
    ) -> None:
        self._provider = provider
        self._prompt = prompt
        self._settings = settings
        self._cache = cache

    async def generate(
        self,
        request: HigherAnswerRequest,
        request_id: str,
    ) -> HigherAnswerResponse:
        response, cache_status = await self._cache.get_or_create(
            self._cache_key(request),
            lambda: self._generate_uncached(request, request_id),
        )
        record_server_cache_event(
            status=cache_status,
            enabled=self._settings.detailed_usage_logging_enabled,
            request_type="higher_answer",
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

    async def _generate_uncached(
        self,
        request: HigherAnswerRequest,
        request_id: str,
    ) -> HigherAnswerResponse:
        provider_result = await self._provider.evaluate(
            system_prompt=self._prompt,
            user_payload=request.model_dump(mode="json", by_alias=True),
            response_model=CompactHigherAnswerOutput,
            request_type="higher_answer",
            max_output_tokens=self._settings.higher_answer_max_output_tokens,
            prompt_cache_key=self._prompt_cache_key(),
        )
        try:
            output = CompactHigherAnswerOutput.model_validate(
                provider_result.output.model_dump()
            )
            validate_improvement_sentences(output.sentences, minimum=12, maximum=15)
            return HigherAnswerResponse(
                answer=_answer(output.sentences, "next"),
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

    def _cache_key(self, request: HigherAnswerRequest) -> str:
        return EvaluationV2Service._hash(
            {
                "kind": "higher-answer",
                "model": self._settings.evaluation_model,
                "promptVersion": self._settings.higher_answer_prompt_version,
                "schemaVersion": self._settings.higher_answer_schema_version,
                "promptHash": hashlib.sha256(self._prompt.encode("utf-8")).hexdigest(),
                "request": request.model_dump(mode="json", by_alias=True),
            }
        )

    def _prompt_cache_key(self) -> str:
        return (
            f"opic:higher-answer:{self._settings.evaluation_model}:"
            f"{self._settings.higher_answer_prompt_version}:"
            f"{self._settings.higher_answer_schema_version}"
        )
