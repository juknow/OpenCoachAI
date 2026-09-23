from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from app.config import Settings, get_settings
from app.providers.openai_provider import OpenAIProvider

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


@lru_cache
def read_prompt(filename: str) -> str:
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


def get_transcription_provider(settings: Settings = Depends(get_settings)) -> OpenAIProvider:
    return OpenAIProvider(settings)


def get_evaluation_provider(settings: Settings = Depends(get_settings)) -> OpenAIProvider:
    return OpenAIProvider(settings)
