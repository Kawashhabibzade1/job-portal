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


def _northcyprus_cv_url(query: str, location: str) -> str:
    params = {}
    if query:
        params["keyword"] = query
    if location:
        params["location"] = location
    suffix = f"?{urlencode(params)}" if params else ""
    return f"https://northcyprus.cv/jobs/{suffix}"


def _iskibris_url(query: str, location: str) -> str:
    params = {}
    if query:
        params["search"] = query
    return f"https://www.iskibris.com/jobs?{urlencode(params)}" if params else "https://www.iskibris.com/jobs"


def _trnc_research_url(query: str, location: str) -> str:
    return "https://grad.emu.edu.tr/en/fees/research-assistantships-opportunities"


def _english_jobs_be_url(query: str, location: str) -> str:
    path = f"/jobs/{_slug(query or 'english')}"
    return f"https://englishjobs.be{path}?{urlencode({'format': 'markdown'})}"


def _stepstone_be_url(query: str, location: str) -> str:
    query_slug = _slug(query or "jobs")
    location_slug = _slug(location or "belgium")
    return f"https://www.stepstone.be/jobs/{query_slug}/in-{location_slug}"


def _iamexpat_nl_url(query: str, location: str) -> str:
    return f"https://www.iamexpat.nl/career/jobs-netherlands?{urlencode({'language': 'english'})}"


def _undutchables_nl_url(query: str, location: str) -> str:
    params = {}
    if location:
        params["location"] = location
    suffix = f"?{urlencode(params)}" if params else ""
    return f"https://undutchables.nl/vacancies{suffix}"


def _bcf_career_nl_url(query: str, location: str) -> str:
    return "https://www.bcfcareer.nl/p/6/jobs"


def _leiden_bioscience_nl_url(query: str, location: str) -> str:
    params = {}
    if query:
        params["search"] = query
    suffix = f"?{urlencode(params)}" if params else ""
    return f"https://jobs.leidenbiosciencepark.nl/vacancies{suffix}"


def _academictransfer_nl_url(query: str, location: str) -> str:
    params = {}
    if query:
        params["q"] = query
    return f"https://www.academictransfer.com/en/jobs/?{urlencode(params)}" if params else "https://www.academictransfer.com/en/jobs/"


def _strip_markdown(value: str | None) -> str | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"[*_`]+", "", cleaned)
    return _clean(cleaned)


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


def _parse_english_jobs_be(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    blocks = re.findall(
        r"\[###\s+(.*?)\]\((.*?)\)\s*(.*?)(?=\n\[###\s+|\nreport probem|\Z)",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for title, href, body in blocks:
        bullets = [
            item
            for item in (
                _strip_markdown(match)
                for match in re.findall(r"^\*\s+(.+)$", body, flags=re.MULTILINE)
            )
            if item
        ]
        description = re.sub(r"^\*\s+.+$", "", body, flags=re.MULTILINE)
        description = _strip_markdown(description)
        if description and description.lower().startswith("logo"):
            description = _strip_markdown(description[4:])

        results.append(
            JobPosting(
                title=_strip_markdown(title) or "",
                company=bullets[0] if bullets else None,
                location=_portal_location(portal, bullets[1] if len(bullets) > 1 else None),
                description=description,
                source=portal.source,
                source_url=_absolute_url(portal, href),
                apply_url=_absolute_url(portal, href),
                date_posted=bullets[2] if len(bullets) > 2 else None,
                is_remote="remote" in " ".join([title, body]).lower(),
            )
        )

    return results[:25]


def _parse_stepstone_be(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    seen: set[str] = set()

    for script in re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        try:
            payload = json.loads(html.unescape(script))
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph") if isinstance(item.get("@graph"), list) else [item]
            for entry in graph:
                if not isinstance(entry, dict) or entry.get("@type") != "JobPosting":
                    continue
                url = _absolute_url(portal, entry.get("url"))
                if not url or url in seen:
                    continue
                seen.add(url)
                hiring = entry.get("hiringOrganization") or {}
                location = entry.get("jobLocation")
                if isinstance(location, list):
                    location = location[0] if location else {}
                address = location.get("address") if isinstance(location, dict) else {}
                location_text = ", ".join(
                    item
                    for item in [
                        address.get("addressLocality") if isinstance(address, dict) else None,
                        address.get("addressCountry") if isinstance(address, dict) else None,
                    ]
                    if item
                )
                results.append(
                    JobPosting(
                        title=_clean(entry.get("title")) or "",
                        company=hiring.get("name") if isinstance(hiring, dict) else None,
                        location=_portal_location(portal, location_text or None),
                        description=_clean(entry.get("description")),
                        source=portal.source,
                        source_url=url,
                        apply_url=url,
                        date_posted=entry.get("datePosted"),
                        is_remote="remote" in json.dumps(entry).lower(),
                    )
                )

    if results:
        return results[:25]

    for match in re.finditer(
        r'<a[^>]+href="([^"]*(?:/jobs?/|/job/)[^"]*)"[^>]*>(.*?)</a>',
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        url = _absolute_url(portal, match.group(1))
        title = _clean(match.group(2))
        if not url or url in seen or not title or len(title) < 6:
            continue
        seen.add(url)
        results.append(
            JobPosting(
                title=title,
                location=_portal_location(portal, None),
                source=portal.source,
                source_url=url,
                apply_url=url,
                is_remote="remote" in match.group(0).lower(),
            )
        )

    return results[:25]


def _parse_iamexpat_nl(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    seen: set[str] = set()
    blocks = re.findall(
        r'(<a(?=[^>]*class="[^"]*JobBoardItemCard_cardWrapper__[^"]*")[^>]*>)(.*?)(?=</a>)',
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for tag, block in blocks:
        href = _attr(tag, "href")
        url = _absolute_url(portal, href)
        if not url or url in seen:
            continue
        seen.add(url)
        title_match = re.search(
            r'<span[^>]+class="[^"]*title-7[^"]*"[^>]*>(.*?)</span>',
            block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not title_match:
            continue

        category = re.search(
            r'<div[^>]+class="[^"]*uppercase[^"]*"[^>]*>(.*?)</div>',
            block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        plain_lines = [
            item
            for item in (_clean(line) for line in re.findall(r"</svg>\s*([^<]+)</div>", block))
            if item
        ]
        posted = next((line.replace("Posted date ", "") for line in plain_lines if line.startswith("Posted date ")), None)
        locations = [line for line in plain_lines if not line.startswith("Posted date ")]

        results.append(
            JobPosting(
                title=_clean(title_match.group(1)) or "",
                location=_portal_location(portal, locations[0] if locations else None),
                description=_clean(category.group(1)) if category else "English-speaking role",
                source=portal.source,
                source_url=url,
                apply_url=url,
                date_posted=posted,
                is_remote="remote" in block.lower() or "hybrid" in block.lower(),
            )
        )

    return results[:25]


def _parse_undutchables_nl(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    seen: set[str] = set()
    blocks = re.findall(
        r'(<a(?=[^>]*class="vacancy-item")[^>]*>)(.*?)</a>',
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for tag, block in blocks:
        href = _attr(tag, "href")
        url = _absolute_url(portal, href)
        if not url or url in seen:
            continue
        title = re.search(r"<h4[^>]*>(.*?)</h4>", block, flags=re.DOTALL | re.IGNORECASE)
        if not title:
            continue
        seen.add(url)
        location = re.search(
            r'<div[^>]+class="location"[^>]*>(.*?)</div>',
            block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        title_text = _clean(title.group(1)) or ""

        results.append(
            JobPosting(
                title=title_text,
                location=_portal_location(portal, _clean(location.group(1)) if location else None),
                description="International and multilingual Netherlands vacancy",
                source=portal.source,
                source_url=url,
                apply_url=url,
                is_remote="remote" in title_text.lower() or "hybrid" in title_text.lower(),
            )
        )

    return results[:25]


def _parse_bcf_career_nl(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    seen: set[str] = set()
    blocks = re.findall(
        r'<(?:article|div|li)[^>]+class="[^"]*(?:vacancy|job)[^"]*"[^>]*>.*?</(?:article|div|li)>',
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for block in blocks:
        if "no jobs found" in block.lower() or "no vacancies were found" in block.lower():
            continue
        link = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.DOTALL | re.IGNORECASE)
        title = _clean(link.group(2)) if link else None
        if not title:
            heading = re.search(r"<h[2-4][^>]*>(.*?)</h[2-4]>", block, flags=re.DOTALL | re.IGNORECASE)
            title = _clean(heading.group(1)) if heading else None
        if not title or len(title) < 5:
            continue

        url = _absolute_url(portal, link.group(1)) if link else portal.base_url
        if not url or url in seen:
            continue
        seen.add(url)

        company = re.search(
            r'class="[^"]*(?:company|employer|organisation)[^"]*"[^>]*>(.*?)</',
            block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        location = re.search(
            r'class="[^"]*(?:location|place)[^"]*"[^>]*>(.*?)</',
            block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        results.append(
            JobPosting(
                title=title,
                company=_clean(company.group(1)) if company else None,
                location=_portal_location(portal, _clean(location.group(1)) if location else None),
                description="Life sciences, biotech, chemistry, food, and pharma vacancy",
                source=portal.source,
                source_url=url,
                apply_url=url,
                is_remote="remote" in block.lower() or "hybrid" in block.lower(),
            )
        )

    return results[:25]


def _parse_leiden_bioscience_nl(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    seen: set[str] = set()
    blocks = re.findall(
        r'<div[^>]+class="[^"]*card[^"]*"[^>]*>.*?(?=<div[^>]+wire:snapshot="[^"]*components\.vacancy-item|</div>\s*</div>\s*</div>\s*<footer)',
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for block in blocks:
        if "components.vacancy-item" not in block:
            continue
        key = None
        key_match = re.search(r'&quot;key&quot;:&quot;([^&]+)&quot;,&quot;s&quot;:&quot;mdl&quot;', block)
        if key_match:
            key = html.unescape(key_match.group(1))
        title_match = re.search(
            r'<a[^>]+class="[^"]*h4[^"]*"[^>]+title="([^"]+)"',
            block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        title = _clean(title_match.group(1)) if title_match else None
        if not title:
            continue

        url = f"{portal.base_url}/vacancies/{key}" if key else portal.base_url + "/vacancies"
        if url in seen:
            continue
        seen.add(url)
        company = re.search(r'<img[^>]+(?:title|alt)="([^"]+)"', block, flags=re.DOTALL | re.IGNORECASE)
        locations = re.findall(
            r'<div[^>]+title="([^"]*Netherlands[^"]*)"[^>]*>',
            block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        categories = re.findall(
            r'<div[^>]+class="[^"]*label[^"]*"[^>]*>(.*?)</div>',
            block,
            flags=re.DOTALL | re.IGNORECASE,
        )
        description = " | ".join(item for item in (_clean(category) for category in categories) if item)

        results.append(
            JobPosting(
                title=title,
                company=_clean(company.group(1)) if company else None,
                location=_portal_location(portal, locations[0] if locations else "Leiden"),
                description=description or "Leiden Bio Science Park life sciences vacancy",
                source=portal.source,
                source_url=url,
                apply_url=url,
                is_remote="remote" in block.lower() or "hybrid" in block.lower(),
            )
        )

    return results[:25]


def _parse_academictransfer_nl(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    seen: set[str] = set()
    for match in re.finditer(
        r'https://www\.academictransfer\.com/en/jobs/(\d+)/([^/"\\]+?)/',
        text,
        flags=re.IGNORECASE,
    ):
        job_id, slug = match.groups()
        if slug == "apply":
            continue
        url = f"https://www.academictransfer.com/en/jobs/{job_id}/{slug}/"
        if url in seen or "/apply/" in url:
            continue
        seen.add(url)
        title = _clean(slug.replace("-", " ").title())
        window = text[max(0, match.start() - 2500) : min(len(text), match.end() + 2500)]
        employer = re.search(r'"name":\s*"([^"]+)"', window)
        city = re.search(r'"city":\s*"([^"]+)"', window)
        if not city:
            city = re.search(r'\b(Amsterdam|Rotterdam|Leiden|Utrecht|Delft|Wageningen|Groningen|Maastricht|Eindhoven|Enschede|Tilburg)\b', window)

        results.append(
            JobPosting(
                title=title or "",
                company=html.unescape(employer.group(1)) if employer else None,
                location=_portal_location(portal, city.group(1) if city else None),
                description="Academic, PhD, postdoc, research, or university-level Netherlands vacancy",
                source=portal.source,
                source_url=url,
                apply_url=url,
                is_remote="remote" in window.lower() or "hybrid" in window.lower(),
            )
        )
        if len(results) >= 25:
            break

    return results


def _parse_northcyprus_cv(text: str, portal: Portal) -> list[JobPosting]:
    results: list[JobPosting] = []
    seen: set[str] = set()
    for match in re.finditer(
        r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        text,
        flags=re.DOTALL,
    ):
        href = match.group(1)
        if "/job/" not in href and "/jobs/" not in href:
            continue

        title_text = _clean(match.group(2))
        if not title_text or len(title_text) < 12:
            continue
        title_lower = title_text.lower()
        if (
            title_lower in {"browse jobs", "find jobs now", "search jobs now"}
            or "quick search" in title_lower
            or "jobs & listings" in title_lower
        ):
            continue

        url = _absolute_url(portal, href)
        if not url or url in seen:
            continue
        seen.add(url)

        parts = [part.strip() for part in title_text.split("|") if part.strip()]
        title = parts[0]
        company = parts[1] if len(parts) > 1 else None
        location = None
        for candidate in ["Nicosia", "Lefkosa", "Lefkoşa", "Kyrenia", "Girne", "Famagusta", "Gazimağusa", "Iskele", "Güzelyurt", "Lefke"]:
            if candidate.lower() in title_text.lower():
                location = candidate
                break

        results.append(
            JobPosting(
                title=title,
                company=company,
                location=_portal_location(portal, location),
                description=_clean(title_text),
                source=portal.source,
                source_url=url,
                apply_url=url,
                is_remote="remote" in title_text.lower(),
            )
        )

    return results[:25]


def _research_query_matches(query: str) -> bool:
    query = query.lower()
    terms = [
        "academic",
        "assistant",
        "biolog",
        "biomed",
        "biotech",
        "ciu",
        "embryo",
        "emu",
        "fertil",
        "human ivf",
        "ivf",
        "lab",
        "labor",
        "lecturer",
        "medical",
        "molekular",
        "neu",
        "phd",
        "professor",
        "research",
        "university",
    ]
    return any(term in query for term in terms)


def _parse_trnc_research_portals(text: str, portal: Portal) -> list[JobPosting]:
    description = (
        "Research and academic application portal for Northern Cyprus. "
        "Relevant for university, laboratory, biomedical, IVF, graduate, and research assistant searches."
    )
    return [
        JobPosting(
            title="Research Assistantship Opportunities",
            company="Eastern Mediterranean University",
            location="Famagusta, Northern Cyprus",
            description=description,
            source=portal.source,
            source_url="https://grad.emu.edu.tr/en/fees/research-assistantships-opportunities",
            apply_url="https://grad.emu.edu.tr/en/fees/research-assistantships-opportunities",
            is_remote=False,
        ),
        JobPosting(
            title="Academic and Research Career Opportunities",
            company="Near East University",
            location="Nicosia, Northern Cyprus",
            description=description,
            source=portal.source,
            source_url="https://neu.edu.tr/career/career-opportunities/?lang=en",
            apply_url="https://neu.edu.tr/career/career-opportunities/?lang=en",
            is_remote=False,
        ),
        JobPosting(
            title="Academic and Administrative Open Positions",
            company="Cyprus International University",
            location="Nicosia, Northern Cyprus",
            description=description,
            source=portal.source,
            source_url="https://ciu.edu.tr/en/careers",
            apply_url="https://intranet.ciu.edu.tr/hr/career-apply",
            is_remote=False,
        ),
    ]


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
    "english_jobs_be": Portal(
        source="EnglishJobs.be",
        base_url="https://englishjobs.be",
        url_builder=_english_jobs_be_url,
        parser=_parse_english_jobs_be,
        country_name="Belgium",
    ),
    "stepstone_be": Portal(
        source="StepStone Belgium",
        base_url="https://www.stepstone.be",
        url_builder=_stepstone_be_url,
        parser=_parse_stepstone_be,
        country_name="Belgium",
    ),
    "iamexpat_nl": Portal(
        source="IamExpat Netherlands",
        base_url="https://www.iamexpat.nl",
        url_builder=_iamexpat_nl_url,
        parser=_parse_iamexpat_nl,
        country_name="Netherlands",
    ),
    "undutchables_nl": Portal(
        source="Undutchables",
        base_url="https://undutchables.nl",
        url_builder=_undutchables_nl_url,
        parser=_parse_undutchables_nl,
        country_name="Netherlands",
    ),
    "bcf_career_nl": Portal(
        source="BCF Career",
        base_url="https://www.bcfcareer.nl",
        url_builder=_bcf_career_nl_url,
        parser=_parse_bcf_career_nl,
        country_name="Netherlands",
    ),
    "leiden_bioscience_nl": Portal(
        source="Leiden Bio Science Park",
        base_url="https://jobs.leidenbiosciencepark.nl",
        url_builder=_leiden_bioscience_nl_url,
        parser=_parse_leiden_bioscience_nl,
        country_name="Netherlands",
    ),
    "academictransfer_nl": Portal(
        source="AcademicTransfer",
        base_url="https://www.academictransfer.com",
        url_builder=_academictransfer_nl_url,
        parser=_parse_academictransfer_nl,
        country_name="Netherlands",
    ),
    "northcyprus_cv": Portal(
        source="NorthCyprus.cv",
        base_url="https://northcyprus.cv",
        url_builder=_northcyprus_cv_url,
        parser=_parse_northcyprus_cv,
        country_name="Northern Cyprus",
    ),
    "iskibris": Portal(
        source="İş Kıbrıs",
        base_url="https://www.iskibris.com",
        url_builder=_iskibris_url,
        parser=_parse_closed_or_blocked,
        country_name="Northern Cyprus",
    ),
    "trnc_research": Portal(
        source="TRNC Research Portals",
        base_url="https://grad.emu.edu.tr",
        url_builder=_trnc_research_url,
        parser=_parse_trnc_research_portals,
        country_name="Northern Cyprus",
    ),
}


def search_portal(portal_key: str, query: str, location: str = "") -> list[JobPosting]:
    portal = PORTALS[portal_key]
    if not query.strip():
        query = "jobs"
    if portal_key == "trnc_research" and not _research_query_matches(query):
        return []
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
        if portal_key not in {"northcyprus_cv", "iskibris"} and query.lower() not in " ".join(
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


def search_english_jobs_be(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("english_jobs_be", query, location)


def search_iamexpat_nl(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("iamexpat_nl", query, location)


def search_undutchables_nl(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("undutchables_nl", query, location)


def search_bcf_career_nl(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("bcf_career_nl", query, location)


def search_leiden_bioscience_nl(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("leiden_bioscience_nl", query, location)


def search_academictransfer_nl(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("academictransfer_nl", query, location)


def search_stepstone_be(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("stepstone_be", query, location)


def search_northcyprus_cv(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("northcyprus_cv", query, location)


def search_iskibris(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("iskibris", query, location)


def search_trnc_research(query: str, location: str = "") -> list[JobPosting]:
    return search_portal("trnc_research", query, location)
