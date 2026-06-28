import re
import unicodedata

from app.models import JobPosting


NORTHERN_CYPRUS_QUERY_MARKERS = {
    "kktc",
    "north cyprus",
    "northern cyprus",
    "nord cyprus",
    "nord zypern",
    "nordzypern",
    "trnc",
    "turkish republic of northern cyprus",
    "turkische republik nordzypern",
    "zypern nord",
}

NORTHERN_CYPRUS_LOCATION_MARKERS = {
    "famagusta",
    "gazimagusa",
    "girne",
    "guzelyurt",
    "iskele",
    "kktc",
    "kyrenia",
    "lefke",
    "lefkosia",
    "lefkosa",
    "north cyprus",
    "northern cyprus",
    "trnc",
    "turkish republic of northern cyprus",
}

REMOTE_LOCATION_MARKERS = {
    "anywhere",
    "emea",
    "europe",
    "global",
    "remote",
    "worldwide",
}

COUNTRY_LOCATION_MARKERS = {
    "at": {
        "austria",
        "osterreich",
        "österreich",
        "vienna",
        "wien",
        "graz",
        "linz",
        "salzburg",
        "innsbruck",
        "klagenfurt",
    },
    "ch": {
        "switzerland",
        "schweiz",
        "suisse",
        "svizzera",
        "zurich",
        "zürich",
        "geneva",
        "geneve",
        "genève",
        "basel",
        "bern",
        "lausanne",
        "lugano",
    },
    "de": {
        "germany",
        "deutschland",
        "berlin",
        "munich",
        "munchen",
        "münchen",
        "hamburg",
        "frankfurt",
        "cologne",
        "koln",
        "köln",
        "stuttgart",
        "dusseldorf",
        "düsseldorf",
    },
    "gb": {
        "united kingdom",
        "uk",
        "great britain",
        "england",
        "scotland",
        "wales",
        "northern ireland",
        "london",
        "manchester",
        "birmingham",
        "leeds",
        "glasgow",
        "edinburgh",
        "bristol",
    },
    "tr": NORTHERN_CYPRUS_LOCATION_MARKERS,
}


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.lower()))


def is_northern_cyprus_query(location: str | None) -> bool:
    normalized = _normalize(location)
    return any(marker in normalized for marker in NORTHERN_CYPRUS_QUERY_MARKERS)


def provider_location_query(location: str) -> str:
    if is_northern_cyprus_query(location):
        return "Northern Cyprus"
    return location


def _is_remote_match(location: str, is_remote: bool | None) -> bool:
    normalized = _normalize(location)
    return bool(is_remote) or any(marker in normalized for marker in REMOTE_LOCATION_MARKERS)


def is_remote_job(job: JobPosting) -> bool:
    return _is_remote_match(job.location or "", job.is_remote)


def location_text_matches(
    job_location: str | None,
    requested_location: str | None,
    is_remote: bool | None = None,
) -> bool:
    normalized_request = _normalize(requested_location)
    if not normalized_request:
        return True

    normalized_job_location = _normalize(job_location)
    if _is_remote_match(normalized_job_location, is_remote):
        return True

    if is_northern_cyprus_query(requested_location):
        return any(marker in normalized_job_location for marker in NORTHERN_CYPRUS_LOCATION_MARKERS)

    return normalized_request in normalized_job_location


def filter_jobs_by_location(jobs: list[JobPosting], requested_location: str) -> list[JobPosting]:
    return [
        job
        for job in jobs
        if location_text_matches(job.location, requested_location, job.is_remote)
    ]


def filter_jobs_by_remote(jobs: list[JobPosting], include_remote: bool) -> list[JobPosting]:
    if include_remote:
        return jobs
    return [job for job in jobs if not is_remote_job(job)]


def country_text_matches(
    job_location: str | None,
    country: str,
    is_remote: bool | None = None,
    include_remote: bool = False,
) -> bool:
    normalized_location = _normalize(job_location)
    markers = COUNTRY_LOCATION_MARKERS.get(country.lower(), set())
    return bool(normalized_location) and any(
        _normalize(marker) in normalized_location for marker in markers
    )


def filter_jobs_by_countries(
    jobs: list[JobPosting],
    countries: list[str],
    include_remote: bool = False,
) -> list[JobPosting]:
    if not countries:
        return jobs
    return [
        job
        for job in jobs
        if any(
            country_text_matches(job.location, country, job.is_remote, include_remote)
            for country in countries
        )
    ]
