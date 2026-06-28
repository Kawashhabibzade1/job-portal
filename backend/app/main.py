from collections.abc import Callable

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import JobPosting, JobSearchResponse
from app.providers.adzuna import search_adzuna
from app.providers.arbeitsagentur import search_arbeitsagentur
from app.providers.arbeitnow import search_arbeitnow
from app.providers.jsearch import search_jsearch
from app.providers.jooble import search_jooble
from app.providers.portal_search import (
    search_jobs_ch,
    search_jobup_ch,
    search_karriere_at,
    search_reed_uk,
)
from app.providers.remotive import search_remotive
from app.services.deduplicate import deduplicate_jobs
from app.services.location import filter_jobs_by_location, provider_location_query
from app.services.normalize import normalize_jobs
from app.services.query_expansion import expanded_job_queries, expanded_relevance_terms
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
    "karriere_at": search_karriere_at,
    "jobs_ch": search_jobs_ch,
    "jobup_ch": search_jobup_ch,
    "reed_uk": search_reed_uk,
}


@app.get("/api/health")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _selected_sources(sources: str | None) -> list[str]:
    if not sources:
        return list(PROVIDERS.keys())
    selected = [source.strip().lower() for source in sources.split(",") if source.strip()]
    return [source for source in selected if source in PROVIDERS]


def _source_key(source: str) -> str:
    return source.lower().replace(".", "_").replace("-", "_").replace(" ", "_")


def _run_provider(
    source: str,
    provider: Provider,
    query: str,
    location: str,
    country: str,
) -> list[JobPosting]:
    if source == "adzuna":
        return provider(query, location, country)
    return provider(query, location)


@app.get("/jobs/search", response_model=JobSearchResponse)
@app.get("/api/jobs/search", response_model=JobSearchResponse)
def search_jobs(
    query: str = Query(default="", description="Job title, skill, or company"),
    location: str = Query(default="", description="City, country, or remote"),
    country: str = Query(default="de", min_length=2, max_length=2),
    sources: str | None = Query(default=None, description="Comma-separated source keys"),
) -> JobSearchResponse:
    selected_sources = _selected_sources(sources)
    jobs: list[JobPosting] = []
    errors: dict[str, str] = {}
    source_counts: dict[str, int] = {source: 0 for source in selected_sources}
    search_queries = expanded_job_queries(query)
    search_location = provider_location_query(location)

    for source in selected_sources:
        for search_query in search_queries:
            try:
                provider_jobs = _run_provider(
                    source,
                    PROVIDERS[source],
                    query=search_query,
                    location=search_location,
                    country=country,
                )
                jobs.extend(provider_jobs)
            except Exception as exc:
                errors[source] = str(exc)
                break

    normalized = normalize_jobs(jobs)
    normalized = filter_jobs_by_location(normalized, location)
    normalized = filter_jobs_by_any_term(normalized, expanded_relevance_terms(query))
    relevance_query = "" if len(search_queries) > 1 else query
    normalized = filter_relevant_jobs(normalized, relevance_query)
    unique = deduplicate_jobs(normalized)
    for job in unique:
        source_key = _source_key(job.source)
        source_counts[source_key] = source_counts.get(source_key, 0) + 1

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
) -> JobSearchResponse:
    return search_jobs(query=query, location=location, country=country, sources=sources)
