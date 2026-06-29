from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import RLock


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= now - self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True


scrape_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
