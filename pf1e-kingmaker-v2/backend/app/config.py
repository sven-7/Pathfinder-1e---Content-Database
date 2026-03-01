"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./runs/pf1e_v2.db")
    app_env: str = os.getenv("APP_ENV", "dev")
    app_name: str = "PF1e Kingmaker V2 API"
    app_version: str = "0.1.0"


settings = Settings()
