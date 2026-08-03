"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for AutoMed."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    openai_api_base: str = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_API_BASE",
    )
    openai_temperature: float = Field(default=0.2, alias="OPENAI_TEMPERATURE")

    hitl_enabled: bool = Field(default=True, alias="HITL_ENABLED")
    hitl_require_approval_for_treatment: bool = Field(
        default=True,
        alias="HITL_REQUIRE_APPROVAL_FOR_TREATMENT",
    )
    hitl_require_approval_for_mental_health: bool = Field(
        default=True,
        alias="HITL_REQUIRE_APPROVAL_FOR_MENTAL_HEALTH",
    )

    fda_api_key: Optional[str] = Field(default=None, alias="FDA_API_KEY")
    nih_api_base: str = Field(
        default="https://clinicaltables.nlm.nih.gov/api",
        alias="NIH_API_BASE",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_group_chat_rounds: int = Field(default=12, alias="MAX_GROUP_CHAT_ROUNDS")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
