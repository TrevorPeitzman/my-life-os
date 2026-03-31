from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Required ---
    API_KEY: str

    # --- Paths ---
    VAULT_DIR: Path = Path("/app/vault")
    CONFIG_DIR: Path = Path("/app/config")

    # --- Timezone ---
    TZ: str = "America/New_York"

    # --- CORS ---
    CORS_ORIGINS: str = "https://localhost"

    # --- VAPID ---
    VAPID_PRIVATE_KEY: str | None = None
    VAPID_PUBLIC_KEY: str | None = None
    VAPID_EMAIL: str | None = None

    # --- AI ---
    AI_PROVIDER: Literal["mistral", "claude-code", "disabled"] = "disabled"
    MISTRAL_API_KEY: str | None = None
    MISTRAL_MODEL: str = "mistral-small-latest"

    # --- Google Calendar ---
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    GOOGLE_CALENDAR_IDS: str = "primary"
    GOOGLE_CALENDAR_WRITE_ID: str = "primary"

    # --- Limits ---
    MAX_DAILY_FILE_BYTES: int = 524288  # 512 KB

    @property
    def cors_origins_list(self) -> list[str]:
        return [s.strip() for s in self.CORS_ORIGINS.split(",") if s.strip()]

    @property
    def calendar_ids_list(self) -> list[str]:
        return [s.strip() for s in self.GOOGLE_CALENDAR_IDS.split(",") if s.strip()]

    @model_validator(mode="after")
    def create_directories(self) -> "Settings":
        self.VAULT_DIR.mkdir(parents=True, exist_ok=True)
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Create vault subdirectories for all planning horizons
        for subdir in ("daily", "weekly", "monthly", "quarterly", "yearly", "goals", "projects"):
            (self.VAULT_DIR / subdir).mkdir(parents=True, exist_ok=True)
        logger.info("Vault: %s | Config: %s | TZ: %s", self.VAULT_DIR, self.CONFIG_DIR, self.TZ)
        return self


settings = Settings()  # type: ignore[call-arg]
