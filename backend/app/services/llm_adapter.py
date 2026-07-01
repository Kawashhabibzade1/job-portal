import json
import os
from typing import Any

import requests

from app.env import load_environment


load_environment()


class LlmAdapter:
    def __init__(self) -> None:
        self.openai_key = _secret("OPENAI_API_KEY")
        self.grok_key = _secret("GROK_API_KEY") or _secret("XAI_API_KEY")
        self.gemini_key = _secret("GEMINI_API_KEY") or _secret("GOOGLE_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.grok_model = os.getenv("GROK_MODEL", "grok-4")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.default_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        self.judge_provider = os.getenv("JUDGE_PROVIDER", "gemini").lower()
        self.timeout = int(os.getenv("LLM_TIMEOUT", "30"))

    def available_providers(self) -> list[str]:
        providers = []
        if self.openai_key:
            providers.append("openai")
        if self.grok_key:
            providers.append("grok")
        if self.gemini_key:
            providers.append("gemini")
        return providers

    def status(self) -> dict[str, object]:
        return {
            "available": self.available_providers(),
            "default_provider": self.default_provider or self._preferred_provider(),
            "models": {
                "openai": self.openai_model if self.openai_key else None,
                "grok": self.grok_model if self.grok_key else None,
                "gemini": self.gemini_model if self.gemini_key else None,
            },
        }

    def manual_mode_note(self) -> str:
        available = self.available_providers()
        if available:
            return f"AI provider configured: {', '.join(available)}."
        return (
            "No AI provider key is connected yet. Add a Gemini, Grok, or OpenAI key in "
            "Profile > AI providers; until then I will keep helping with built-in career tools."
        )

    def ask_default(self, system: str, user: str) -> tuple[str, str]:
        provider = self._preferred_provider()
        if provider == "gemini":
            return self.ask_gemini(system, user), "gemini"
        if provider == "grok":
            return self.ask_grok(system, user), "grok"
        if provider == "openai":
            return self.ask_openai(system, user), "openai"
        raise MissingKeyError("No LLM API key is configured.")

    def ask_openai(self, system: str, user: str) -> str:
        if not self.openai_key:
            raise MissingKeyError("OPENAI_API_KEY is not configured.")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.openai_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def ask_grok(self, system: str, user: str) -> str:
        if not self.grok_key:
            raise MissingKeyError("GROK_API_KEY or XAI_API_KEY is not configured.")
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.grok_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.grok_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def ask_gemini(self, system: str, user: str) -> str:
        if not self.gemini_key:
            raise MissingKeyError("GEMINI_API_KEY or GOOGLE_API_KEY is not configured.")
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent"
        )
        response = requests.post(
            endpoint,
            params={"key": self.gemini_key},
            headers={"Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0.2},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return _gemini_text(data)

    def _preferred_provider(self) -> str:
        available = self.available_providers()
        if self.default_provider in available:
            return self.default_provider
        for provider in ("gemini", "grok", "openai"):
            if provider in available:
                return provider
        return ""


class MissingKeyError(Exception):
    pass


def _gemini_text(data: dict[str, Any]) -> str:
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()


def _secret(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    value = value.strip()
    lowered = value.lower()
    if lowered.startswith("your_") or lowered in {"changeme", "optional"}:
        return None
    return value


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {}
