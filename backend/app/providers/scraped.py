from __future__ import annotations

import html
import random
import re
import time
from datetime import datetime, timezone
from collections.abc import Callable
from urllib.parse import quote_plus, urljoin, urlparse

import requests

from app.config import settings
from app.models import JobPosting
from app.services.cache import cache_key, job_cache
from app.services.logger import logger, timed_log


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36",
]

SOURCE_PRIORITY = {"Indeed": 0, "LinkedIn": 1, "StepStone": 2}


class ScraperBlockedError(RuntimeError):
    pass


class ScraperMarkupError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de,en;q=0.9",
    }


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip() or None


def _attr(markup: str, name: str) -> str | None:
    patterns = [
        rf"\b{name}=['\"]([^'\"]*)['\"]",
        rf"\b{name}=([^'\"\s>]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, markup, flags=re.IGNORECASE)
        if match:
            return html.unescape(match.group(1))
    return None


def _text_by_attr(markup: str, attr_name: str, attr_value: str) -> str | None:
    match = re.search(
        rf"<[^>]+\b{attr_name}=['\"]{re.escape(attr_value)}['\"][^>]*>(.*?)</[^>]+>",
        markup,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return _clean(match.group(1)) if match else None


def _text_by_class(markup: str, class_name: str) -> str | None:
    match = re.search(
        rf"<[^>]+\bclass=['\"][^'\"]*{re.escape(class_name)}[^'\"]*['\"][^>]*>(.*?)</[^>]+>",
        markup,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return _clean(match.group(1)) if match else None


def _safe_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    url = urljoin(base_url, html.unescape(href))
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    return url


def _blocked_reason(response: requests.Response) -> str | None:
    server = response.headers.get("server", "").lower()
    mitigated = response.headers.get("cf-mitigated", "").lower()
    text = response.text[:5000].lower()
    if mitigated == "challenge":
        return "Cloudflare challenge"
    if response.status_code in {403, 408, 409, 425, 429}:
        return f"HTTP {response.status_code}"
    if "cloudflare" in server and ("just a moment" in text or "challenge" in text):
        return "Cloudflare challenge"
    captcha_markers = [
        "please verify you are a human",
        "captcha challenge",
        "unusual traffic",
        "security check",
    ]
    if any(marker in text for marker in captcha_markers):
        return "anti-bot challenge"
    return None


def _fetch_with_retry(url: str, source: str) -> str:
    last_error: Exception | None = None
    for attempt in range(1, settings.scraper_max_retries + 1):
        try:
            response = requests.get(
                url,
                headers=_headers(),
                timeout=settings.scraper_timeout_ms / 1000,
            )
            if response.status_code == 404:
                return ""
            blocked_reason = _blocked_reason(response)
            if blocked_reason:
                raise ScraperBlockedError(f"{source} blocked the request: {blocked_reason}")
            if response.status_code in {500, 502, 503, 504}:
                raise ScraperBlockedError(f"{source} returned HTTP {response.status_code}")
            response.raise_for_status()
            return response.text
        except (requests.RequestException, ScraperBlockedError) as exc:
            last_error = exc
            logger.warning("%s scrape attempt %s failed: %s", source, attempt, exc)
            if attempt < settings.scraper_max_retries:
                time.sleep(min(2**attempt, 5))
    raise RuntimeError(f"{source} scrape failed after retries: {last_error}")


def _cache_or_fetch(
    query: str,
    location: str,
    source: str,
    refresh: bool,
    fetcher: Callable[[], list[JobPosting]],
) -> list[JobPosting]:
    key = cache_key(query, location, source)
    if not refresh:
        cached = job_cache.get(key)
        if cached is not None:
            logger.info("cache hit source=%s key=%s", source, key)
            return cached  # type: ignore[return-value]

    logger.info("cache miss source=%s key=%s", source, key)
    try:
        jobs = fetcher()
        job_cache.set(key, jobs)
        return jobs
    except Exception:
        cached = job_cache.get(key)
        if cached is not None:
            logger.warning("returning stale cached data source=%s key=%s", source, key)
            return cached  # type: ignore[return-value]
        raise


def _stamp(source: str) -> tuple[str, list[str]]:
    return source, [source]


def search_indeed(query: str, location: str = "", refresh: bool = False) -> list[JobPosting]:
    def fetch() -> list[JobPosting]:
        url = (
            "https://de.indeed.com/jobs?"
            f"q={quote_plus(query or '')}&l={quote_plus(location or '')}"
        )
        with timed_log("scrape", source="Indeed", query=query, location=location):
            text = _fetch_with_retry(url, "Indeed")
            jobs = _parse_indeed(text)
            if not jobs and text.strip():
                raise ScraperMarkupError(
                    "Indeed did not return job cards. The request is likely blocked by "
                    "Indeed anti-bot protection or the public markup changed."
                )
            logger.info("scrape count source=Indeed count=%s", len(jobs))
            return jobs

    return _cache_or_fetch(query, location, "indeed", refresh, fetch)


def search_linkedin(query: str, location: str = "", refresh: bool = False) -> list[JobPosting]:
    def fetch() -> list[JobPosting]:
        url = (
            "https://www.linkedin.com/jobs/search/?"
            f"keywords={quote_plus(query or '')}&location={quote_plus(location or '')}"
        )
        with timed_log("scrape", source="LinkedIn", query=query, location=location):
            text = _fetch_with_retry(url, "LinkedIn")
            jobs = _parse_linkedin(text)
            if not jobs and text.strip():
                raise ScraperMarkupError(
                    "LinkedIn did not return job cards. The request is likely blocked by "
                    "LinkedIn anti-bot protection or the public markup changed."
                )
            logger.info("scrape count source=LinkedIn count=%s", len(jobs))
            return jobs

    return _cache_or_fetch(query, location, "linkedin", refresh, fetch)


def _parse_indeed(text: str) -> list[JobPosting]:
    now = datetime.now(timezone.utc).isoformat()
    source, sources = _stamp("Indeed")
    jobs: list[JobPosting] = []
    cards = re.findall(
        r"<[^>]+data-testid=['\"]job-card['\"][^>]*>.*?</div>\s*</div>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not cards:
        cards = re.findall(
            r"<div[^>]+class=['\"][^'\"]*job_seen_beacon[^'\"]*['\"][^>]*>.*?</table>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

    for card in cards[:50]:
        link_match = re.search(r"<h2[^>]*>.*?<a([^>]*)>(.*?)</a>", card, re.DOTALL | re.I)
        title = _clean(link_match.group(2)) if link_match else None
        href = _attr(link_match.group(1), "href") if link_match else None
        if not title:
            title = _text_by_attr(card, "data-testid", "jobTitle")
        if not title:
            continue

        salary = _text_by_attr(card, "data-testid", "salary")
        jobs.append(
            JobPosting(
                title=title,
                company=_text_by_attr(card, "data-testid", "company-name"),
                location=_text_by_attr(card, "data-testid", "job-location"),
                description=_clean(card)[:600] if _clean(card) else None,
                source=source,
                sources=sources,
                source_url=_safe_url("https://de.indeed.com", href),
                apply_url=_safe_url("https://de.indeed.com", href),
                salary_text=salary,
                scraped_at=now,
                is_remote="remote" in card.lower() or "homeoffice" in card.lower(),
            )
        )
    return jobs


def _parse_linkedin(text: str) -> list[JobPosting]:
    now = datetime.now(timezone.utc).isoformat()
    source, sources = _stamp("LinkedIn")
    jobs: list[JobPosting] = []
    cards = re.findall(
        r"<[^>]+data-job-id=['\"][^'\"]+['\"][^>]*>.*?</li>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not cards:
        cards = re.findall(
            r"<div[^>]+class=['\"][^'\"]*base-search-card[^'\"]*['\"][^>]*>.*?</div>\s*</div>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

    for card in cards[:50]:
        title = _text_by_class(card, "base-search-card__title")
        if not title:
            continue
        link = _safe_url("https://www.linkedin.com", _attr(card, "href"))
        if not link:
            job_id = _attr(card, "data-job-id")
            link = _safe_url("https://www.linkedin.com", f"/jobs/view/{job_id}") if job_id else None
        jobs.append(
            JobPosting(
                title=title,
                company=_text_by_class(card, "base-search-card__company-name"),
                location=_text_by_class(card, "job-search-card__location"),
                description=_clean(card)[:600] if _clean(card) else None,
                source=source,
                sources=sources,
                source_url=link,
                apply_url=link,
                scraped_at=now,
                is_remote="remote" in card.lower(),
            )
        )
    return jobs
