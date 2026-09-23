from functools import lru_cache, partial
from pathlib import Path
from threading import Lock

from fastapi import Depends

from app.config import Settings, get_settings
from app.errors import ApiProblem
from app.providers.base import TranscriptionProvider
from app.providers.local_whisper_provider import LocalWhisperTranscriptionProvider
from app.providers.openai_provider import OpenAIEvaluationProvider, OpenAITranscriptionProvider

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
_local_whisper_load_lock = Lock()


@lru_cache
def read_prompt(filename: str) -> str:
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def _cached_local_whisper_model(model_name: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_name, device="cpu", compute_type="int8")


def load_local_whisper_model(model_name: str):
    with _local_whisper_load_lock:
        try:
            return _cached_local_whisper_model(model_name)
        except Exception as error:
            raise ApiProblem(
                "LOCAL_STT_UNAVAILABLE",
                "로컬 음성 인식 모델을 준비하지 못했습니다. "
                "모델 저장소와 서버 설정을 확인해 주세요.",
                503,
            ) from error


def get_transcription_provider(
    settings: Settings = Depends(get_settings),
) -> TranscriptionProvider:
    if settings.transcription_provider == "local_whisper":
        return LocalWhisperTranscriptionProvider(
            model_loader=partial(load_local_whisper_model, settings.local_whisper_model),
            model_name=settings.local_whisper_model,
        )
    return OpenAITranscriptionProvider(settings)


def get_evaluation_provider(settings: Settings = Depends(get_settings)) -> OpenAIEvaluationProvider:
    return OpenAIEvaluationProvider(settings)
