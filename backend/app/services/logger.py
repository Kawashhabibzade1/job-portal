from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from collections.abc import Iterator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("job-portal")


@contextmanager
def timed_log(action: str, **fields: object) -> Iterator[None]:
    started = time.perf_counter()
    logger.info("%s start %s", action, fields)
    try:
        yield
    except Exception:
        logger.exception("%s failed %s", action, fields)
        raise
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000)
        logger.info("%s end duration_ms=%s %s", action, duration_ms, fields)
