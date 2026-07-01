from pathlib import Path
import os

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
LOCAL_ENV_FILE = BACKEND_DIR / ".env"
ALLOWED_RUNTIME_KEYS = {
    "OPENAI_API_KEY",
    "GROK_API_KEY",
    "XAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "LLM_PROVIDER",
    "OPENAI_MODEL",
    "GROK_MODEL",
    "GEMINI_MODEL",
    "JUDGE_PROVIDER",
    "LLM_TIMEOUT",
}


def load_environment() -> None:
    for path in (
        ROOT_DIR / ".env",
        ROOT_DIR / ".env.local",
        BACKEND_DIR / ".env",
        BACKEND_DIR / ".env.local",
    ):
        if path.exists():
            load_dotenv(path, override=False)


def save_runtime_environment(values: dict[str, str]) -> Path:
    existing = _read_env_file(LOCAL_ENV_FILE)
    for key, value in values.items():
        if key not in ALLOWED_RUNTIME_KEYS:
            continue
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        existing[key] = cleaned
        os.environ[key] = cleaned

    _write_env_file(LOCAL_ENV_FILE, existing)
    return LOCAL_ENV_FILE


def _read_env_file(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() in ALLOWED_RUNTIME_KEYS:
            values[key.strip()] = value.strip()
    return values


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Local AI provider settings. This file is ignored by git."]
    for key in sorted(values):
        lines.append(f"{key}={values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
