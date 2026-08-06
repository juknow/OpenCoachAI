from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ai_provider: Literal["local"] = "local"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    ollama_context_length: int = Field(default=8_192, ge=2_048, le=32_768)
    ollama_max_concurrent_evaluations: int = Field(default=1, ge=1, le=8)
    ollama_timeout_seconds: float = Field(default=600, ge=10, le=600)
    ollama_invalid_response_max_retries: int = Field(default=1, ge=0, le=3)
    ollama_keep_alive: str = "10m"
    ollama_evaluation_max_output_tokens: int = Field(default=4_000, ge=1_600, le=8_000)
    ollama_higher_answer_max_output_tokens: int = Field(default=900, ge=500, le=2_000)
    whisper_model: str = "small.en"
    whisper_device: Literal["cpu"] = "cpu"
    whisper_compute_type: Literal["int8"] = "int8"
    whisper_cpu_threads: int = Field(default=4, ge=1, le=32)
    whisper_language: Literal["en"] = "en"
    whisper_local_files_only: bool = True
    whisper_vad_enabled: bool = True
    whisper_vad_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    whisper_vad_min_speech_duration_ms: int = Field(default=0, ge=0, le=10_000)
    whisper_vad_min_silence_duration_ms: int = Field(default=1_000, ge=0, le=10_000)
    whisper_vad_speech_pad_ms: int = Field(default=500, ge=0, le=5_000)
    app_environment: Literal["development", "test", "production"] = "development"
    usage_log_enabled: bool = False
    evaluation_prompt_version: Literal["v1", "v2"] = "v2"
    evaluation_schema_version: Literal["v1", "v2"] = "v2"
    evaluation_v2_prompt_version: Literal["v1"] = "v1"
    evaluation_v2_schema_version: Literal["v1"] = "v1"
    higher_answer_prompt_version: Literal["v1"] = "v1"
    higher_answer_schema_version: Literal["v1"] = "v1"
    evaluation_cache_ttl_seconds: int = Field(default=300, ge=0, le=3_600)
    evaluation_cache_max_entries: int = Field(default=128, ge=1, le=10_000)
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_audio_bytes: int = Field(default=900_000, ge=1_024, le=25_000_000)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def detailed_usage_logging_enabled(self) -> bool:
        return self.app_environment == "development" and self.usage_log_enabled

    @property
    def evaluation_model(self) -> str:
        return self.ollama_model

    @property
    def transcription_model(self) -> str:
        return self.whisper_model

    @property
    def evaluation_max_output_tokens(self) -> int:
        return self.ollama_evaluation_max_output_tokens

    @property
    def higher_answer_max_output_tokens(self) -> int:
        return self.ollama_higher_answer_max_output_tokens


@lru_cache
def get_settings() -> Settings:
    return Settings()
