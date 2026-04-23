from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    app_name: str = "Setu Reconciliation Service"
    app_version: str = "1.0.0"
    default_page_size: int = 50
    max_page_size: int = 200

    def __init__(self) -> None:
        raw_database_url = os.getenv("DATABASE_URL", "sqlite:///./setu.db")
        if raw_database_url.startswith("postgres://"):
            raw_database_url = raw_database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif raw_database_url.startswith("postgresql://"):
            raw_database_url = raw_database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        self.database_url = raw_database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
