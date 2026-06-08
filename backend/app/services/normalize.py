import html
import re
from datetime import datetime, timezone

from app.models import JobPosting


WHITESPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")


def _compact_text(value: str | None) -> str | None:
    if value is None:
        return None
    return WHITESPACE_RE.sub(" ", html.unescape(str(value))).strip()


def _plain_description(value: str | None) -> str | None:
    if not value:
        return None
    without_tags = TAG_RE.sub(" ", value)
    text = _compact_text(without_tags)
    return text[:4000] if text else None


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None

    value = str(value).strip()
    if value.isdigit():
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return value

    return value


def normalize_job(job: JobPosting) -> JobPosting:
    payload = job.model_dump() if hasattr(job, "model_dump") else job.dict()
    payload["title"] = _compact_text(payload.get("title")) or ""
    payload["company"] = _compact_text(payload.get("company"))
    payload["location"] = _compact_text(payload.get("location"))
    payload["description"] = _plain_description(payload.get("description"))
    payload["date_posted"] = _normalize_date(payload.get("date_posted"))

    remote_text = " ".join(
        value.lower()
        for value in [
            payload.get("title"),
            payload.get("location"),
            payload.get("description"),
        ]
        if value
    )
    if payload.get("is_remote") is None and "remote" in remote_text:
        payload["is_remote"] = True

    return JobPosting(**payload)


def normalize_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    return [normalize_job(job) for job in jobs if job.title.strip()]

