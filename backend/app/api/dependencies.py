from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from app.config import Settings, get_settings
from app.providers.base import AiProvider, EvaluationProvider, TranscriptionProvider
from app.providers.local_provider import LocalAiProvider

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


@lru_cache
def read_prompt(filename: str) -> str:
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


_provider_instance: AiProvider | None = None
_provider_settings: Settings | None = None


def _provider_for(settings: Settings) -> AiProvider:
    global _provider_instance, _provider_settings
    if _provider_instance is not None and _provider_settings == settings:
        return _provider_instance
    provider: AiProvider = LocalAiProvider(settings)
    _provider_instance = provider
    _provider_settings = settings
    return provider


def get_ai_provider(settings: Settings = Depends(get_settings)) -> AiProvider:
    return _provider_for(settings)


def get_transcription_provider(
    provider: AiProvider = Depends(get_ai_provider),
) -> TranscriptionProvider:
    return provider


def get_evaluation_provider(
    provider: AiProvider = Depends(get_ai_provider),
) -> EvaluationProvider:
    return provider
