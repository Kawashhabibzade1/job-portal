import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.models import JobPosting


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "msclkid"}


def _clean(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def _canonical_url(value: str | None) -> str:
    if not value:
        return ""

    parsed = urlparse(value)
    filtered_query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in TRACKING_KEYS and not key.startswith(TRACKING_PREFIXES)
    ]

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            urlencode(filtered_query),
            "",
        )
    )


def _job_key(job: JobPosting) -> tuple[str, str, str, str]:
    link = _canonical_url(job.apply_url or job.source_url)
    return (
        _clean(job.title),
        _clean(job.company),
        _clean(job.location),
        link,
    )


def deduplicate_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[JobPosting] = []

    for job in jobs:
        key = _job_key(job)
        fallback_key = key[:3] + ("",)
        if key in seen or fallback_key in seen:
            continue

        seen.add(key)
        if key[3]:
            seen.add(fallback_key)
        unique.append(job)

    return unique

