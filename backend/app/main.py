from collections.abc import Callable

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import JobPosting, JobSearchResponse
from app.providers.adzuna import search_adzuna
from app.providers.arbeitsagentur import search_arbeitsagentur
from app.providers.arbeitnow import search_arbeitnow
from app.providers.jsearch import search_jsearch
from app.providers.jooble import search_jooble
from app.providers.portal_search import (
    search_arcs_community,
    search_healthjobs_uk,
    search_ifs_uk,
    search_jobs_ch,
    search_jobs_ac_uk,
    search_jobup_ch,
    search_karriere_at,
    search_new_scientist_jobs,
    search_nhs_jobs,
    search_northcyprus_cv,
    search_iskibris,
    search_trnc_research,
    search_reed_uk,
)
from app.providers.remotive import search_remotive
from app.providers.scraped import search_indeed, search_linkedin
from app.services.cache import job_cache
from app.services.deduplicate import deduplicate_jobs
from app.services.logger import logger
from app.services.location import (
    filter_jobs_by_countries,
    filter_jobs_by_location,
    filter_jobs_by_remote,
    provider_location_query,
)
from app.services.normalize import normalize_jobs
from app.services.query_expansion import expanded_job_queries, expanded_relevance_terms
from app.services.rate_limit import scrape_rate_limiter
from app.services.relevance import filter_jobs_by_any_term, filter_relevant_jobs


Provider = Callable[..., list[JobPosting]]

app = FastAPI(title="Job Portal API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PROVIDERS: dict[str, Provider] = {
    "arbeitsagentur": search_arbeitsagentur,
    "arbeitnow": search_arbeitnow,
    "adzuna": search_adzuna,
    "remotive": search_remotive,
    "jsearch": search_jsearch,
    "jooble": search_jooble,
    "indeed": search_indeed,
    "linkedin": search_linkedin,
    "karriere_at": search_karriere_at,
    "jobs_ch": search_jobs_ch,
    "jobup_ch": search_jobup_ch,
    "reed_uk": search_reed_uk,
    "nhs_jobs": search_nhs_jobs,
    "healthjobs_uk": search_healthjobs_uk,
    "jobs_ac_uk": search_jobs_ac_uk,
    "new_scientist_jobs": search_new_scientist_jobs,
    "ifs_uk": search_ifs_uk,
    "arcs_community": search_arcs_community,
    "northcyprus_cv": search_northcyprus_cv,
    "iskibris": search_iskibris,
    "trnc_research": search_trnc_research,
}

SUPPORTED_COUNTRIES = {
    "at": "Austria",
    "ch": "Switzerland",
    "de": "Germany",
    "gb": "United Kingdom",
    "tr": "Northern Cyprus",
}

SOURCE_COUNTRIES = {
    "arbeitsagentur": {"de"},
    "arbeitnow": {"de"},
    "indeed": {"de"},
    "linkedin": {"de"},
    "karriere_at": {"at"},
    "jobs_ch": {"ch"},
    "jobup_ch": {"ch"},
    "reed_uk": {"gb"},
    "nhs_jobs": {"gb"},
    "healthjobs_uk": {"gb"},
    "jobs_ac_uk": {"gb"},
    "new_scientist_jobs": {"gb"},
    "ifs_uk": {"gb"},
    "arcs_community": {"gb"},
    "northcyprus_cv": {"tr"},
    "iskibris": {"tr"},
    "trnc_research": {"tr"},
}


@app.get("/api/health")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _selected_sources(sources: str | None) -> list[str]:
    if not sources:
        return list(SOURCE_COUNTRIES.keys())
    selected = [source.strip().lower() for source in sources.split(",") if source.strip()]
    return [source for source in selected if source in PROVIDERS]


def _source_key(source: str) -> str:
    return source.lower().replace(".", "_").replace("-", "_").replace(" ", "_")


def _selected_countries(country: str) -> list[str]:
    requested = [
        item.strip().lower()
        for item in country.split(",")
        if item.strip() and item.strip().lower() != "all"
    ]
    raw_requested = [item.strip().lower() for item in country.split(",") if item.strip()]
    if not requested or "all" in raw_requested:
        return list(SUPPORTED_COUNTRIES.keys())
    return [item for item in requested if item in SUPPORTED_COUNTRIES]


def _source_supports_country(source: str, country: str) -> bool:
    supported = SOURCE_COUNTRIES.get(source)
    return bool(supported and country in supported)


def _provider_location(source: str, location: str, country: str) -> str:
    if not location.strip() and source in SOURCE_COUNTRIES and source not in {"indeed", "linkedin"}:
        return ""

    country_name = SUPPORTED_COUNTRIES.get(country, "")
    if location.strip():
        location_query = provider_location_query(location)
        if country_name and country_name.lower() not in location_query.lower():
            return f"{location_query}, {country_name}"
        return location_query
    return country_name


def _run_provider(
    source: str,
    provider: Provider,
    query: str,
    location: str,
    country: str,
    refresh: bool = False,
) -> list[JobPosting]:
    if source == "adzuna":
        return provider(query, location, country)
    if source in {"indeed", "linkedin"}:
        return provider(query, location, refresh)
    return provider(query, location)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _scrape_sources(sources: str | None) -> list[str]:
    if not sources:
        return ["indeed", "linkedin"]
    selected = [source.strip().lower() for source in sources.split(",") if source.strip()]
    return [source for source in selected if source in {"indeed", "linkedin"}]


@app.get("/jobs/search", response_model=JobSearchResponse)
@app.get("/api/jobs/search", response_model=JobSearchResponse)
def search_jobs(
    query: str = Query(default="", description="Job title, skill, or company"),
    location: str = Query(default="", description="City, country, or remote"),
    country: str = Query(default="de", description="Country code, all, or comma-separated country codes"),
    sources: str | None = Query(default=None, description="Comma-separated source keys"),
    include_remote: bool = Query(default=False, description="Include remote jobs"),
    refresh: bool = Query(default=False, description="Bypass scraper cache"),
) -> JobSearchResponse:
    selected_countries = _selected_countries(country)
    selected_sources = [
        source
        for source in _selected_sources(sources)
        if any(_source_supports_country(source, search_country) for search_country in selected_countries)
    ]
    jobs: list[JobPosting] = []
    errors: dict[str, str] = {}
    source_counts: dict[str, int] = {source: 0 for source in selected_sources}
    search_queries = expanded_job_queries(query)

    for source in selected_sources:
        for search_country in selected_countries:
            if not _source_supports_country(source, search_country):
                continue
            search_location = _provider_location(source, location, search_country)
            for search_query in search_queries:
                try:
                    provider_jobs = _run_provider(
                        source,
                        PROVIDERS[source],
                        query=search_query,
                        location=search_location,
                        country=search_country,
                        refresh=refresh,
                    )
                    jobs.extend(provider_jobs)
                except Exception as exc:
                    errors[source] = str(exc)
                    break

    normalized = normalize_jobs(jobs)
    normalized = filter_jobs_by_remote(normalized, include_remote)
    if location.strip():
        normalized = filter_jobs_by_location(normalized, location)
    else:
        normalized = filter_jobs_by_countries(normalized, selected_countries, include_remote)
    normalized = filter_jobs_by_any_term(normalized, expanded_relevance_terms(query))
    relevance_query = "" if len(search_queries) > 1 else query
    normalized = filter_relevant_jobs(normalized, relevance_query)
    unique = deduplicate_jobs(normalized)
    for job in unique:
        source_key = _source_key(job.source)
        source_counts[source_key] = source_counts.get(source_key, 0) + 1
    source_counts = {source: count for source, count in source_counts.items() if count > 0}

    return JobSearchResponse(
        query=query,
        location=location,
        country=country,
        count=len(unique),
        jobs=unique,
        sources=source_counts,
        errors=errors,
    )


@app.get("/jobs", response_model=JobSearchResponse)
@app.get("/api/jobs", response_model=JobSearchResponse)
def search_jobs_alias(
    query: str = "",
    location: str = "",
    country: str = "de",
    sources: str | None = None,
    include_remote: bool = False,
) -> JobSearchResponse:
    return search_jobs(
        query=query,
        location=location,
        country=country,
        sources=sources,
        include_remote=include_remote,
    )


@app.get("/api/jobs/scrape", response_model=JobSearchResponse)
def scrape_jobs(
    request: Request,
    query: str = Query(default="", description="Job title, skill, or company"),
    location: str = Query(default="", description="City or region"),
    sources: str | None = Query(default=None, description="indeed,linkedin"),
    refresh: bool = Query(default=False, description="Bypass cache"),
) -> JobSearchResponse:
    client_key = _client_key(request)
    if not scrape_rate_limiter.allow(client_key):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded. Try again in a minute.",
                "source": "System",
                "fallbackData": None,
            },
        )

    selected_sources = _scrape_sources(sources)
    jobs: list[JobPosting] = []
    errors: dict[str, str] = {}
    source_counts: dict[str, int] = {source: 0 for source in selected_sources}

    for source in selected_sources:
        try:
            provider_jobs = _run_provider(
                source,
                PROVIDERS[source],
                query=query,
                location=location,
                country="de",
                refresh=refresh,
            )
            jobs.extend(provider_jobs)
        except Exception as exc:
            logger.exception("scrape endpoint failed source=%s", source)
            errors[source] = str(exc)

    normalized = normalize_jobs(jobs)
    unique = deduplicate_jobs(normalized)
    for job in unique:
        source_counts[_source_key(job.source)] = source_counts.get(_source_key(job.source), 0) + 1

    return JobSearchResponse(
        query=query,
        location=location,
        country="de",
        count=len(unique),
        jobs=unique,
        sources=source_counts,
        errors=errors,
    )


@app.get("/api/jobs/cache")
def cache_stats() -> dict[str, int]:
    return job_cache.stats()


@app.delete("/api/jobs/cache")
def clear_cache(prefix: str | None = None) -> dict[str, int]:
    removed = job_cache.delete_prefix(prefix) if prefix else job_cache.clear()
    return {"removed": removed}


@app.post("/api/jobs/deduplicate")
def deduplicate_endpoint(
    jobs: list[JobPosting] = Body(...),
) -> dict[str, object]:
    unique = deduplicate_jobs(normalize_jobs(jobs))
    return {"count": len(unique), "jobs": unique}
