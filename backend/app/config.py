import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _secret(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None

    value = value.strip()
    lowered = value.lower()
    if lowered.startswith("your_") or lowered in {"changeme", "optional"}:
        return None

    return value


@dataclass(frozen=True)
class Settings:
    adzuna_app_id: str | None
    adzuna_app_key: str | None
    jsearch_api_key: str | None
    jooble_api_key: str | None
    cors_origins: list[str]


@lru_cache
def get_settings() -> Settings:
    return Settings(
        adzuna_app_id=_secret("ADZUNA_APP_ID"),
        adzuna_app_key=_secret("ADZUNA_APP_KEY"),
        jsearch_api_key=_secret("JSEARCH_API_KEY"),
        jooble_api_key=_secret("JOOBLE_API_KEY"),
        cors_origins=_split_csv(
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            )
        ),
    )


settings = get_settings()
