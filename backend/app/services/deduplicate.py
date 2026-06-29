import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.models import JobPosting


SOURCE_PRIORITY = {"Indeed": 0, "LinkedIn": 1, "StepStone": 2}
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


def _title_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0
    return SequenceMatcher(None, left, right).ratio()


def _priority(job: JobPosting) -> int:
    return SOURCE_PRIORITY.get(job.source, 99)


def _merge_jobs(primary: JobPosting, duplicate: JobPosting) -> JobPosting:
    if _priority(duplicate) < _priority(primary):
        primary, duplicate = duplicate, primary

    payload = primary.model_dump() if hasattr(primary, "model_dump") else primary.dict()
    other = duplicate.model_dump() if hasattr(duplicate, "model_dump") else duplicate.dict()
    sources = []
    for source in [*payload.get("sources", []), payload.get("source"), *other.get("sources", []), other.get("source")]:
        if source and source not in sources:
            sources.append(source)
    payload["sources"] = sources

    for field in [
        "company",
        "location",
        "description",
        "source_url",
        "apply_url",
        "date_posted",
        "scraped_at",
        "salary_text",
        "salary_min",
        "salary_max",
        "currency",
        "is_remote",
    ]:
        if payload.get(field) in {None, ""} and other.get(field) not in {None, ""}:
            payload[field] = other[field]

    return JobPosting(**payload)


def _is_duplicate(left: JobPosting, right: JobPosting) -> bool:
    left_title = _clean(left.title)
    right_title = _clean(right.title)
    left_company = _clean(left.company)
    right_company = _clean(right.company)
    if not left_company or left_company != right_company:
        return False
    if left_title == right_title:
        return True
    return _title_similarity(left_title, right_title) >= 0.85


def deduplicate_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[JobPosting] = []

    for job in jobs:
        if not job.sources:
            job.sources.append(job.source)
        key = _job_key(job)
        fallback_key = key[:3] + ("",)

        merged = False
        for index, existing in enumerate(unique):
            if _is_duplicate(existing, job):
                unique[index] = _merge_jobs(existing, job)
                merged = True
                break
        if merged:
            continue

        if key in seen or fallback_key in seen:
            continue

        seen.add(key)
        if key[3]:
            seen.add(fallback_key)
        unique.append(job)

    return unique
