from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: SecretStr | None = None
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
    openai_evaluation_model: str = "gpt-5.6-luna"
    openai_timeout_seconds: float = Field(default=60, ge=5, le=180)
    openai_max_retries: int = Field(default=2, ge=0, le=5)
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_audio_bytes: int = Field(default=900_000, ge=1_024, le=25_000_000)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ):
        del settings_cls, file_secret_settings

        def environment_without_api_key() -> dict[str, object]:
            values = dict(env_settings())
            values.pop("openai_api_key", None)
            values.pop("OPENAI_API_KEY", None)
            return values

        # The API key may come from explicit test injection or backend/.env only.
        # Other deployment settings, including ALLOWED_ORIGINS, may use process env.
        return init_settings, environment_without_api_key, dotenv_settings

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value().strip())

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
