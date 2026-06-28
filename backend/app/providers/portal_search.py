from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote, urlencode, urljoin

import requests

from app.models import JobPosting


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobPortal/0.1; +https://example.local)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en,de;q=0.9,fr;q=0.8",
}


@dataclass(frozen=True)
class Portal:
    source: str
    base_url: str
    url_builder: Callable[[str, str], str]
    parser: Callable[[str, "Portal"], list[JobPosting]]
    country_name: str | None = None


def _clean(value: str | None) -> str | None:
    if not value:
        return None

    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip() or None


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", " ", value.lower(), flags=re.UNICODE)
    cleaned = re.sub(r"[\s_]+", "-", cleaned).strip("-")
    return quote(cleaned)


def _absolute_url(portal: Portal, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(portal.base_url, html.unescape(href))


def _portal_location(portal: Portal, location: str | None) -> str | None:
    if not location:
        return portal.country_name
    if portal.country_name and portal.country_name.lower() not in location.lower():
        return f"{location}, {portal.country_name}"
    return location


def _attr(markup: str, name: str) -> str | None:
    match = re.search(rf'\b{name}="([^"]*)"', markup)
    return html.unescape(match.group(1)) if match else None


def _extract_array_after(text: str, marker: str) -> list[dict]:
    marker_index = text.find(marker)
    if marker_index < 0:
        return []

    start = text.find("[", marker_index)
    if start < 0:
        return []

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : index + 1])
                except json.JSONDecodeError:
                    return []

    return []


def _fetch(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text


def _karriere_url(query: str, location: str) -> str:
    path = f"/jobs/{_slug(query or 'jobs')}"
    if location:
        path += f"/{_slug(location)}"
    return f"https://www.karriere.at{path}"


def _swiss_url(host: str, path: str = "/en/vacancies/") -> Callable[[str, str], str]:
    def build(query: str, location: str) -> str:
        params = {"term": query}
        if location:
            params["location"] = location
        return f"https://{host}{path}?{urlencode(params)}"

    return build


def _reed_url(query: str, location: str) -> str:
    query_slug = _slug(query or "jobs")
    if location:
        return f"https://www.reed.co.uk/jobs/{query_slug}-jobs-in-{_slug(location)}"
    return f"https://www.reed.co.uk/jobs/{query_slug}-jobs"


def _nhs_jobs_url(query: str, location: str) -> str:
    params = {"keyword": query, "language": "en"}
    if location:
        params["location"] = location
    return f"https://www.jobs.nhs.uk/candidate/search/results?{urlencode(params)}"


def _healthjobs_uk_url(query: str, location: str) -> str:
    params = {"keyword": query}
    if location:
        params["location"] = location
    return f"https://www.healthjobsuk.com/job_search?{urlencode(params)}"


def _jobs_ac_uk_url(query: str, location: str) -> str:
    params = {"keywords": query}
    if location:
        params["location"] = location
    else:
        params["location"] = "United Kingdom"
    return f"https://www.jobs.ac.uk/search/?{urlencode(params)}"


def _new_scientist_url(query: str, location: str) -> str:
    params = {"keywords": query}
    if location:
        params["location"] = location
    return f"https://jobs.newscientist.com/jobs/?{urlencode(params)}"


def _ifs_url(query: str, location: str) -> str:
    return "https://ifs.org.uk/jobs"


def _arcs_url(query: str, location: str) -> str:
    return "https://www.arcscientists.org/jobs-and-training/"


def _parse_karriere(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    blocks = re.findall(
        r'<li class="m-jobsList__item".*?</li>',
        text,
        flags=re.DOTALL,
    )

    for block in blocks:
        title_link = re.search(
            r'<a class="m-jobsListItem__titleLink"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            block,
            flags=re.DOTALL,
        )
        if not title_link:
            continue

        company = re.search(
            r'<a class="m-jobsListItem__companyName[^"]*"[^>]*>(.*?)</a>',
            block,
            flags=re.DOTALL,
        )
        locations = re.findall(
            r'<span class="m-jobsListItem__location"[^>]*>(.*?)</span>',
            block,
            flags=re.DOTALL,
        )
        pills = re.findall(
            r'<span class="m-jobsListItem__pill"[^>]*>(.*?)</span>',
            block,
            flags=re.DOTALL,
        )

        description = " | ".join(
            item for item in (_clean(pill) for pill in pills) if item
        )
        results.append(
            JobPosting(
                title=_clean(title_link.group(2)) or "",
                company=_clean(company.group(1)) if company else None,
                location=_portal_location(
                    portal,
                    ", ".join(
                        item for item in (_clean(location) for location in locations) if item
                    )
                    or None,
                ),
                description=description or None,
                source=portal.source,
                source_url=_absolute_url(portal, title_link.group(1)),
                apply_url=_absolute_url(portal, title_link.group(1)),
                is_remote="homeoffice" in block.lower() or "remote" in block.lower(),
            )
        )

    return results


def _parse_swiss(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    items = _extract_array_after(text, '"results":{"main":{"results":')
    for item in items[:25]:
        job_id = item.get("id")
        url = _absolute_url(portal, f"/en/vacancies/detail/{job_id}/") if job_id else None
        company = item.get("company") or {}
        results.append(
            JobPosting(
                title=item.get("title") or "",
                company=company.get("name"),
                location=_portal_location(portal, item.get("place")),
                description=item.get("relativeDate"),
                source=portal.source,
                source_url=url,
                apply_url=url,
                date_posted=item.get("publicationDate"),
                is_remote=None,
            )
        )

    if results:
        return results

    for match in re.finditer(
        r'<a[^>]+data-cy="job-link"[^>]+href="([^"]+)"[^>]*title="([^"]+)"',
        text,
        flags=re.DOTALL,
    ):
        results.append(
            JobPosting(
                title=_clean(match.group(2)) or "",
                location=_portal_location(portal, None),
                source=portal.source,
                source_url=_absolute_url(portal, match.group(1)),
                apply_url=_absolute_url(portal, match.group(1)),
            )
        )
    return results[:25]


def _parse_reed(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    blocks = re.findall(
        r'<article[^>]+data-qa="job-card"[^>]*>.*?</article>',
        text,
        flags=re.DOTALL,
    )

    for block in blocks:
        link = re.search(
            r'<a(?=[^>]*data-qa="job-card-title")[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            block,
            flags=re.DOTALL,
        )
        title = (
            _attr(link.group(0), "title")
            if link
            else _attr(block, "title")
        )
        if not title and link:
            title = _clean(link.group(2))
        if not title:
            title_match = re.search(r"jobTitle[^>]*>(.*?)<", block, flags=re.DOTALL)
            title = _clean(title_match.group(1)) if title_match else None
        if not title:
            continue

        company = re.search(
            r'data-qa="job-posted-by"[^>]*>.*? by <a[^>]*>(.*?)</a>',
            block,
            flags=re.DOTALL,
        )
        location = re.search(
            r'data-qa="job-metadata-location"[^>]*>.*?</svg>(.*?)</li>',
            block,
            flags=re.DOTALL,
        )
        summary = re.search(
            r'data-qa="job-card-job-description"[^>]*>(.*?)</',
            block,
            flags=re.DOTALL,
        )

        results.append(
            JobPosting(
                title=title,
                company=_clean(company.group(1)) if company else None,
                location=_portal_location(
                    portal,
                    _clean(location.group(1)) if location else None,
                ),
                description=_clean(summary.group(1)) if summary else None,
                source=portal.source,
                source_url=_absolute_url(portal, link.group(1)) if link else None,
                apply_url=_absolute_url(portal, link.group(1)) if link else None,
                is_remote="remote" in (_clean(location.group(1)) or "").lower()
                if location
                else False,
            )
        )

    return results


def _parse_nhs_jobs(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    blocks = re.findall(
        r'<li class="nhsuk-list-panel search-result[^"]*"[^>]*>.*?</li>\s*</ul>\s*</div>\s*</div>\s*</li>|<li class="nhsuk-list-panel search-result[^"]*"[^>]*>.*?</li>',
        text,
        flags=re.DOTALL,
    )
    if not blocks:
        blocks = re.findall(
            r'<li class="nhsuk-list-panel search-result.*?(?=<li class="nhsuk-list-panel search-result|\s*</ul>)',
            text,
            flags=re.DOTALL,
        )

    for block in blocks:
        title_link = re.search(
            r'<a(?=[^>]*data-test="search-result-job-title")[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            block,
            flags=re.DOTALL,
        )
        if not title_link:
            continue

        location_block = re.search(
            r'data-test="search-result-location"[^>]*>.*?<h3[^>]*>(.*?)</h3>',
            block,
            flags=re.DOTALL,
        )
        location_parts = []
        company = None
        if location_block:
            location_text = _clean(location_block.group(1))
            if location_text:
                lines = [part.strip() for part in location_text.split("  ") if part.strip()]
                company = lines[0] if lines else location_text
                location_parts = lines[1:]

        salary = re.search(r'data-test="search-result-salary"[^>]*>(.*?)</li>', block, re.DOTALL)
        posted = re.search(
            r'data-test="search-result-publicationDate"[^>]*>.*?<strong[^>]*>(.*?)</strong>',
            block,
            re.DOTALL,
        )
        description = " | ".join(
            item
            for item in [
                _clean(salary.group(1)) if salary else None,
                f"Date posted: {_clean(posted.group(1))}" if posted else None,
            ]
            if item
        )

        results.append(
            JobPosting(
                title=_clean(title_link.group(2)) or "",
                company=company,
                location=_portal_location(
                    portal,
                    ", ".join(location_parts) if location_parts else None,
                ),
                description=description or None,
                source=portal.source,
                source_url=_absolute_url(portal, title_link.group(1)),
                apply_url=_absolute_url(portal, title_link.group(1)),
                date_posted=_clean(posted.group(1)) if posted else None,
                is_remote="remote" in block.lower() or "home based" in block.lower(),
            )
        )

    return results[:25]


def _parse_jobs_ac_uk(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    blocks = re.findall(
        r'<div class="j-search-result__result[^"]*"[^>]*>.*?(?=<div class="j-search-result__result|\s*</div>\s*</div>\s*</div>)',
        text,
        flags=re.DOTALL,
    )

    for block in blocks:
        title_link = re.search(r'<a href="([^"]+)">(.*?)</a>', block, flags=re.DOTALL)
        if not title_link:
            continue

        company = re.search(
            r'<div class="j-search-result__employer">\s*<b>(.*?)</b>',
            block,
            flags=re.DOTALL,
        )
        location = re.search(r'<div>\s*Location:\s*(.*?)</div>', block, flags=re.DOTALL)
        salary = re.search(
            r'<div class="j-search-result__info">\s*(.*?)</div>',
            block,
            flags=re.DOTALL,
        )
        posted = re.search(r'<strong>Date Placed: </strong>\s*(.*?)\s*</div>', block, re.DOTALL)

        location_text = _clean(location.group(1)) if location else None
        results.append(
            JobPosting(
                title=_clean(title_link.group(2)) or "",
                company=_clean(company.group(1)) if company else None,
                location=_portal_location(portal, location_text),
                description=_clean(salary.group(1)) if salary else None,
                source=portal.source,
                source_url=_absolute_url(portal, title_link.group(1)),
                apply_url=_absolute_url(portal, title_link.group(1)),
                date_posted=_clean(posted.group(1)) if posted else None,
                is_remote=bool(location_text and "hybrid" in location_text.lower()),
            )
        )

    return results[:25]


def _parse_arcs(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    blocks = re.findall(r'<div class="job_container job-card[^"]*"[^>]*>.*?</div>\s*</div>', text, re.DOTALL)
    for block in blocks:
        link = re.search(r'<div class="job_link">\s*<a href="([^"]+)"', block, re.DOTALL)
        title = re.search(r'<div class="job_title">\s*(.*?)\s*</div>', block, re.DOTALL)
        location = re.search(r'<div class="job_location job-tag">\s*(.*?)\s*</div>', block, re.DOTALL)
        job_type = re.search(r'<div class="job_type job-tag">\s*(.*?)\s*</div>', block, re.DOTALL)
        salary = re.search(r'<div class="salary job-tag">\s*(.*?)\s*</div>', block, re.DOTALL)
        if not title:
            continue

        results.append(
            JobPosting(
                title=_clean(title.group(1)) or "",
                location=_portal_location(portal, _clean(location.group(1)) if location else None),
                description=" | ".join(
                    item
                    for item in [
                        _clean(job_type.group(1)) if job_type else None,
                        _clean(salary.group(1)) if salary else None,
                    ]
                    if item
                )
                or None,
                source=portal.source,
                source_url=_absolute_url(portal, link.group(1)) if link else portal.base_url,
                apply_url=_absolute_url(portal, link.group(1)) if link else portal.base_url,
                is_remote=False,
            )
        )

    return results[:25]


def _parse_ifs(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    blocks = re.findall(r'<article[^>]*>.*?</article>', text, re.DOTALL)
    for block in blocks:
        if "job" not in block.lower() and "vacanc" not in block.lower():
            continue
        link = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
        title = _clean(link.group(2)) if link else None
        if not title:
            heading = re.search(r'<h[2-4][^>]*>(.*?)</h[2-4]>', block, re.DOTALL)
            title = _clean(heading.group(1)) if heading else None
        if not title:
            continue
        results.append(
            JobPosting(
                title=title,
                location=_portal_location(portal, "London"),
                source=portal.source,
                source_url=_absolute_url(portal, link.group(1)) if link else portal.base_url,
                apply_url=_absolute_url(portal, link.group(1)) if link else portal.base_url,
                is_remote=False,
            )
        )
    return results[:25]


def _parse_closed_or_blocked(text: str, portal: Portal) -> list[JobPosting]:
    if "has now closed" in text.lower():
        return []
    return []


PORTALS = {
    "karriere_at": Portal(
        source="Karriere.at",
        base_url="https://www.karriere.at",
        url_builder=_karriere_url,
        parser=_parse_karriere,
        country_name="Austria",
    ),
    "jobs_ch": Portal(
        source="Jobs.ch",
        base_url="https://www.jobs.ch",
        url_builder=_swiss_url("www.jobs.ch"),
        parser=_parse_swiss,
        country_name="Switzerland",
    ),
    "jobup_ch": Portal(
        source="Jobup.ch",
        base_url="https://www.jobup.ch",
        url_builder=_swiss_url("www.jobup.ch", "/en/jobs/"),
        parser=_parse_swiss,
        country_name="Switzerland",
    ),
    "reed_uk": Portal(
        source="Reed UK",
        base_url="https://www.reed.co.uk",
        url_builder=_reed_url,
        parser=_parse_reed,
        country_name="United Kingdom",
    ),
    "nhs_jobs": Portal(
        source="NHS Jobs",
        base_url="https://www.jobs.nhs.uk",
        url_builder=_nhs_jobs_url,
        parser=_parse_nhs_jobs,
        country_name="United Kingdom",
    ),
    "healthjobs_uk": Portal(
        source="HealthJobsUK",
        base_url="https://www.healthjobsuk.com",
        url_builder=_healthjobs_uk_url,
        parser=_parse_closed_or_blocked,
        country_name="United Kingdom",
    ),
    "jobs_ac_uk": Portal(
        source="Jobs.ac.uk",
        base_url="https://www.jobs.ac.uk",
        url_builder=_jobs_ac_uk_url,
        parser=_parse_jobs_ac_uk,
        country_name="United Kingdom",
    ),
    "new_scientist_jobs": Portal(
        source="New Scientist Jobs",
        base_url="https://jobs.newscientist.com",
        url_builder=_new_scientist_url,
        parser=_parse_closed_or_blocked,
        country_name="United Kingdom",
    ),
    "ifs_uk": Portal(
        source="IFS",
        base_url="https://ifs.org.uk/jobs",
        url_builder=_ifs_url,
        parser=_parse_ifs,
        country_name="United Kingdom",
    ),
    "arcs_community": Portal(
        source="ARCS Community",
        base_url="https://www.arcscientists.org",
        url_builder=_arcs_url,
        parser=_parse_arcs,
        country_name="United Kingdom",
    ),
}


def search_portal(portal_key: str, query: str, location: str = "") -> list[JobPosting]:
    portal = PORTALS[portal_key]
    if not query.strip():
        query = "jobs"
    try:
        html_text = _fetch(portal.url_builder(query, location))
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in {403, 404, 406}:
            return []
        raise
    jobs = portal.parser(html_text, portal)
    search_note = f"Search match: {query}"

    tagged_jobs: list[JobPosting] = []
    for job in jobs:
        description = job.description or ""
        if query.lower() not in " ".join(
            value.lower()
            for value in [job.title, job.company, job.location, description]
            if value
        ):
            description = f"{description} | {search_note}" if description else search_note
        if hasattr(job, "model_copy"):
            tagged_jobs.append(job.model_copy(update={"description": description or None}))
        else:
            tagged_jobs.append(job.copy(update={"description": description or None}))

    return tagged_jobs


def search_karriere_at(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("karriere_at", query, location)


def search_jobs_ch(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("jobs_ch", query, location)


def search_jobup_ch(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("jobup_ch", query, location)


def search_reed_uk(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("reed_uk", query, location)


def search_nhs_jobs(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("nhs_jobs", query, location)


def search_healthjobs_uk(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("healthjobs_uk", query, location)


def search_jobs_ac_uk(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("jobs_ac_uk", query, location)


def search_new_scientist_jobs(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("new_scientist_jobs", query, location)


def search_ifs_uk(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("ifs_uk", query, location)


def search_arcs_community(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("arcs_community", query, location)
