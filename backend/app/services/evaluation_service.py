from app.errors import ProviderResponseError
from app.evaluation_defaults import SAFETY_NOTICE, estimated_range_for, reusable_structure_for
from app.providers.base import AiProvider
from app.schemas.common import ResponseMetadata
from app.schemas.evaluation import (
    EvaluationModelOutput,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
)


class EvaluationService:
    def __init__(self, provider: AiProvider, prompt: str) -> None:
        self._provider = provider
        self._prompt = prompt

    async def evaluate(self, request: EvaluationRequest, request_id: str) -> EvaluationResponse:
        payload = request.model_dump(mode="json", by_alias=True)
        provider_result = await self._provider.evaluate(
            system_prompt=self._prompt,
            user_payload=payload,
            response_model=EvaluationModelOutput,
        )

        try:
            parsed = EvaluationModelOutput.model_validate(provider_result.output.model_dump())
            evaluation = EvaluationResult(
                **parsed.model_dump(),
                estimated_range=estimated_range_for(parsed.most_likely_level),
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
        except (TypeError, ValueError) as error:
            raise ProviderResponseError("INVALID_EVALUATION_RESPONSE") from error
