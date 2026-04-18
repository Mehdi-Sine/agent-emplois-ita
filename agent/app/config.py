from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
RUNS_DIR = DATA_DIR / "runs"


@dataclass(slots=True)
class Settings:
    supabase_url: str
    supabase_service_key: str
    archive_missed_threshold: int = 2
    user_agent: str = "ITA Jobs Bot/1.0"
    request_timeout_seconds: int = 20

    @classmethod
    def from_env(cls) -> "Settings":
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        if not supabase_url or not supabase_service_key:
            raise RuntimeError(
                "Les variables SUPABASE_URL et SUPABASE_SERVICE_KEY sont obligatoires."
            )

        archive_missed_threshold = int(
            os.getenv("JOBS_ARCHIVE_MISSED_THRESHOLD", "2").strip()
        )
        user_agent = os.getenv("USER_AGENT", "ITA Jobs Bot/1.0").strip()
        timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20").strip())
        return cls(
            supabase_url=supabase_url,
            supabase_service_key=supabase_service_key,
            archive_missed_threshold=archive_missed_threshold,
            user_agent=user_agent,
            request_timeout_seconds=timeout,
        )


def load_sources_config() -> list[dict[str, Any]]:
    config_path = CONFIG_DIR / "sources.yaml"
    content = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return content.get("sources", [])
