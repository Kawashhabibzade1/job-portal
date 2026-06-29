from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock
from typing import Generic, TypeVar

from app.config import settings


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float
    created_at: float


class MemoryCache:
    def __init__(self) -> None:
        self._items: dict[str, CacheEntry[object]] = {}
        self._lock = RLock()

    def get(self, key: str) -> object | None:
        now = time.time()
        with self._lock:
            entry = self._items.get(key)
            if not entry:
                return None
            if entry.expires_at <= now:
                self._items.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: object, ttl_ms: int | None = None) -> None:
        now = time.time()
        ttl = (ttl_ms if ttl_ms is not None else settings.cache_duration_ms) / 1000
        with self._lock:
            self._items[key] = CacheEntry(value=value, expires_at=now + ttl, created_at=now)

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [key for key in self._items if key.startswith(prefix)]
            for key in keys:
                self._items.pop(key, None)
            return len(keys)

    def clear(self) -> int:
        with self._lock:
            count = len(self._items)
            self._items.clear()
            return count

    def stats(self) -> dict[str, int]:
        now = time.time()
        with self._lock:
            expired = [key for key, entry in self._items.items() if entry.expires_at <= now]
            for key in expired:
                self._items.pop(key, None)
            return {"entries": len(self._items)}


job_cache = MemoryCache()


def cache_key(query: str, location: str, source: str) -> str:
    return "_".join(
        [
            query.strip().lower() or "any",
            location.strip().lower() or "anywhere",
            source.strip().lower(),
        ]
    )
