from collections.abc import Callable
import json
from queue import Empty, Queue
from threading import Thread
import time
from uuid import uuid4

from pathlib import Path

from fastapi import Body, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.config import settings
from app.env import save_runtime_environment
from app.models import (
    AlertCreate,
    ApplicationCreate,
    ApplicationPackageRequest,
    ApplicationPackageResponse,
    ApplicationRecord,
    ApplicationStats,
    ApplicationUpdate,
    ApplyAutomationRequest,
    ApplyAutomationResponse,
    BookmarkedJob,
    ChatRequest,
    ChatResponse,
    DebateRequest,
    DebateResponse,
    CoverLetterRequest,
    CoverLetterResponse,
    DocumentUpdate,
    CvCompareRequest,
    CvCompareResponse,
    CvImproveRequest,
    CvImproveResponse,
    ExportRequest,
    FeedbackRequest,
    FeedbackResponse,
    FollowUpRequest,
    FollowUpResponse,
    GeneratedFile,
    InterviewPrepRequest,
    InterviewPrepResponse,
    JobCompareRequest,
    JobCompareResponse,
    JobMatchRequest,
    JobMatchResponse,
    JobPosting,
    JobSearchResponse,
    LinkedInMessageRequest,
    LinkedInMessageResponse,
    PdfMergeRequest,
    PdfOperationResponse,
    PdfOrganizeRequest,
    ProfileUpdate,
    RoadmapRequest,
    RoadmapResponse,
    SalaryInsightsRequest,
    SalaryInsightsResponse,
    SavedAlert,
    UploadedDocument,
    UserProfile,
    WeeklyReportResponse,
)
from app.providers.adzuna import search_adzuna
from app.providers.arbeitsagentur import search_arbeitsagentur
from app.providers.arbeitnow import search_arbeitnow
from app.providers.jsearch import search_jsearch
from app.providers.jooble import search_jooble
from app.providers.portal_search import (
    search_arcs_community,
    search_english_jobs_be,
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
    search_stepstone_be,
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
from app.services.query_expansion import expanded_job_queries
from app.services.rate_limit import scrape_rate_limiter
from app.services.ai_search import smart_filter_jobs, translated_query_variants
from app.services.agent_orchestrator import classify_intent, handle_chat
from app.services.apply_automation import prepare_apply_automation
from app.services.artifact_service import (
    build_application_package,
    export_cover_letter,
    get_generated_file,
    list_generated_files,
    merge_pdfs,
    organize_pdf,
)
from app.services.career_tools import (
    analyze_feedback,
    build_roadmap,
    compare_cvs,
    improve_cv,
    interview_prep,
)
from app.services.debate_service import run_debate
from app.services.document_builder import create_cover_letter
from app.services.document_service import list_documents, store_upload, update_document
from app.services.llm_adapter import LlmAdapter
from app.services.matching_service import rank_jobs
from app.services.profile_service import (
    create_application,
    get_profile,
    list_applications,
    save_profile,
    update_application,
    update_profile,
)
from app.services.serialization import model_dump
from app.services.salary_insights import salary_insights
from app.services.bookmarks_service import (
    add_bookmark,
    list_bookmarks,
    remove_bookmark,
)
from app.services.extras_service import (
    application_stats,
    compare_jobs,
    create_alert,
    delete_alert,
    generate_follow_up,
    generate_linkedin_message,
    list_alerts,
    weekly_report,
)


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
    "english_jobs_be": search_english_jobs_be,
    "stepstone_be": search_stepstone_be,
    "northcyprus_cv": search_northcyprus_cv,
    "iskibris": search_iskibris,
    "trnc_research": search_trnc_research,
}

SUPPORTED_COUNTRIES = {
    "at": "Austria",
    "be": "Belgium",
    "ch": "Switzerland",
    "de": "Germany",
    "gb": "United Kingdom",
    "tr": "Northern Cyprus",
}

SOURCE_COUNTRIES = {
    "arbeitsagentur": {"de"},
    "arbeitnow": {"de"},
    "indeed": {"de"},
    "linkedin": {"at", "be", "ch", "de", "gb", "tr"},
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
    "english_jobs_be": {"be"},
    "stepstone_be": {"be"},
    "northcyprus_cv": {"tr"},
    "iskibris": {"tr"},
    "trnc_research": {"tr"},
}


@app.get("/api/health")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/llm/status")
def llm_status_endpoint() -> dict[str, object]:
    return LlmAdapter().status()


@app.put("/api/llm/settings")
def llm_settings_endpoint(payload: dict[str, str] = Body(default_factory=dict)) -> dict[str, object]:
    save_runtime_environment(payload)
    return LlmAdapter().status()


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
    search_queries = []
    for search_query in translated_query_variants(query, selected_countries):
        search_queries.extend(expanded_job_queries(search_query))
    search_queries = list(dict.fromkeys(search_queries))

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
    unique = deduplicate_jobs(normalized)
    filter_result = smart_filter_jobs(unique, query, selected_countries)
    unique = filter_result.jobs
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
        search_queries=search_queries,
        ai_filter_provider=filter_result.provider,
        ai_filter_note=filter_result.note,
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
        refresh=False,
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


def _internal_search(
    query: str = "",
    location: str = "",
    country: str = "all",
    sources: str | None = None,
    include_remote: bool = True,
) -> JobSearchResponse:
    return search_jobs(
        query=query,
        location=location,
        country=country,
        sources=sources,
        include_remote=include_remote,
        refresh=False,
    )


@app.post("/api/jobs/chat", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    return handle_chat(payload, _internal_search)


CHAT_STREAM_STATUSES = {
    "search": "Searching live job sources...",
    "match": "Ranking jobs against your profile...",
    "cover_letter": "Drafting your cover letter...",
    "apply": "Preparing application steps. Final submit still needs your confirmation.",
    "tracker": "Loading your application tracker...",
    "cv_improve": "Reviewing your CV and building improvements...",
    "interview": "Preparing interview practice...",
    "roadmap": "Building your skill roadmap...",
    "feedback": "Analyzing the rejection feedback...",
    "career_advice": "Reading your profile and career direction...",
    "profile": "Opening your career profile...",
    "general": "Thinking through your request...",
}


def _sse_event(event: str, data: dict) -> str:
    payload = {"event": event, **data}
    return f"data: {json.dumps(payload, default=str)}\n\n"


def _text_chunks(text: str):
    chunk = ""
    for character in text:
        chunk += character
        if character.isspace() or len(chunk) >= 18:
            yield chunk
            chunk = ""
    if chunk:
        yield chunk


@app.post("/api/jobs/chat/stream")
@app.post("/api/chat/stream")
def chat_stream_endpoint(payload: ChatRequest) -> StreamingResponse:
    conversation_id = payload.conversation_id or str(uuid4())
    if hasattr(payload, "model_copy"):
        live_payload = payload.model_copy(update={"conversation_id": conversation_id})
    else:
        live_payload = payload.copy(update={"conversation_id": conversation_id})
    intent = classify_intent(live_payload.message)
    status = CHAT_STREAM_STATUSES.get(intent, CHAT_STREAM_STATUSES["general"])

    def stream():
        yield _sse_event("conversation", {"conversation_id": conversation_id})
        yield _sse_event("status", {"message": status, "intent": intent})
        result_queue: Queue = Queue(maxsize=1)

        def run_chat() -> None:
            try:
                result_queue.put(("response", handle_chat(live_payload, _internal_search)))
            except Exception as exc:
                result_queue.put(("error", exc))

        Thread(target=run_chat, daemon=True).start()

        while True:
            try:
                kind, result = result_queue.get(timeout=0.45)
                break
            except Empty:
                yield _sse_event("status", {"message": "Still working...", "intent": intent})

        if kind == "error":
            yield _sse_event("error", {"message": str(result)})
            return

        response = result
        for chunk in _text_chunks(response.message):
            yield _sse_event("chunk", {"text": chunk})
            time.sleep(0.006)
        yield _sse_event("response", {"response": model_dump(response)})
        yield _sse_event("done", {})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/documents/upload", response_model=UploadedDocument)
async def upload_document(file: UploadFile = File(...)) -> UploadedDocument:
    return await store_upload(file)


@app.get("/api/documents", response_model=list[UploadedDocument])
def documents_endpoint() -> list[UploadedDocument]:
    return list_documents()


@app.patch("/api/documents/{document_id}", response_model=UploadedDocument)
def update_document_endpoint(document_id: str, payload: DocumentUpdate) -> UploadedDocument:
    document = update_document(document_id, payload)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.get("/api/profile", response_model=UserProfile)
def profile_endpoint() -> UserProfile:
    return get_profile()


@app.put("/api/profile", response_model=UserProfile)
def update_profile_endpoint(payload: ProfileUpdate) -> UserProfile:
    return update_profile(payload)


@app.post("/api/jobs/match", response_model=JobMatchResponse)
def match_jobs_endpoint(payload: JobMatchRequest) -> JobMatchResponse:
    jobs = payload.jobs
    if not jobs and (payload.query or payload.location):
        sources = ",".join(payload.sources) if payload.sources else None
        result = search_jobs(
            query=payload.query,
            location=payload.location,
            country=payload.country,
            sources=sources,
            include_remote=payload.include_remote,
            refresh=False,
        )
        jobs = result.jobs
    matches = rank_jobs(jobs, get_profile(), payload.cv_text)
    return JobMatchResponse(count=len(matches), matches=matches)


@app.post("/api/agents/debate", response_model=DebateResponse)
def debate_endpoint(payload: DebateRequest) -> DebateResponse:
    return run_debate(payload, get_profile())


@app.post("/api/documents/cover-letter", response_model=CoverLetterResponse)
def cover_letter_endpoint(payload: CoverLetterRequest) -> CoverLetterResponse:
    return create_cover_letter(payload, get_profile())


@app.post("/api/documents/export-cover-letter", response_model=GeneratedFile)
def export_cover_letter_endpoint(payload: ExportRequest) -> GeneratedFile:
    return export_cover_letter(payload)


@app.get("/api/documents/generated", response_model=list[GeneratedFile])
def generated_files_endpoint() -> list[GeneratedFile]:
    return list_generated_files()


@app.get("/api/documents/generated/{file_id}/download")
def download_generated_file(file_id: str) -> FileResponse:
    file = get_generated_file(file_id)
    if not file or not Path(file.path).exists():
        raise HTTPException(status_code=404, detail="Generated file not found")
    return FileResponse(file.path, media_type=file.mime_type, filename=file.filename)


@app.post("/api/documents/application-package", response_model=ApplicationPackageResponse)
def application_package_endpoint(payload: ApplicationPackageRequest) -> ApplicationPackageResponse:
    return build_application_package(payload, get_profile())


@app.post("/api/pdf/merge", response_model=PdfOperationResponse)
def merge_pdf_endpoint(payload: PdfMergeRequest) -> PdfOperationResponse:
    try:
        return merge_pdfs(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/pdf/organize", response_model=PdfOperationResponse)
def organize_pdf_endpoint(payload: PdfOrganizeRequest) -> PdfOperationResponse:
    try:
        return organize_pdf(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/cv/improve", response_model=CvImproveResponse)
def improve_cv_endpoint(payload: CvImproveRequest) -> CvImproveResponse:
    return improve_cv(payload, get_profile())


@app.post("/api/cv/compare", response_model=CvCompareResponse)
def compare_cv_endpoint(payload: CvCompareRequest) -> CvCompareResponse:
    return compare_cvs(payload)


@app.post("/api/interview/prepare", response_model=InterviewPrepResponse)
def interview_prep_endpoint(payload: InterviewPrepRequest) -> InterviewPrepResponse:
    return interview_prep(payload, get_profile())


@app.post("/api/feedback/rejection", response_model=FeedbackResponse)
def rejection_feedback_endpoint(payload: FeedbackRequest) -> FeedbackResponse:
    return analyze_feedback(payload, get_profile())


@app.post("/api/roadmap/skills", response_model=RoadmapResponse)
def roadmap_endpoint(payload: RoadmapRequest) -> RoadmapResponse:
    return build_roadmap(payload, get_profile())


@app.post("/api/apply/automation", response_model=ApplyAutomationResponse)
def apply_automation_endpoint(payload: ApplyAutomationRequest) -> ApplyAutomationResponse:
    return prepare_apply_automation(payload, get_profile())


@app.get("/api/applications", response_model=list[ApplicationRecord])
def applications_endpoint() -> list[ApplicationRecord]:
    return list_applications()


@app.post("/api/applications", response_model=ApplicationRecord)
def create_application_endpoint(payload: ApplicationCreate) -> ApplicationRecord:
    return create_application(payload)


@app.patch("/api/applications/{application_id}", response_model=ApplicationRecord)
def update_application_endpoint(
    application_id: str,
    payload: ApplicationUpdate,
) -> ApplicationRecord:
    application = update_application(application_id, payload)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


# --- New feature endpoints ---


@app.post("/api/jobs/salary-insights", response_model=SalaryInsightsResponse)
def salary_insights_endpoint(payload: SalaryInsightsRequest) -> SalaryInsightsResponse:
    return salary_insights(payload)


@app.get("/api/alerts", response_model=list[SavedAlert])
def alerts_list_endpoint() -> list[SavedAlert]:
    return list_alerts()


@app.post("/api/alerts", response_model=SavedAlert)
def alerts_create_endpoint(payload: AlertCreate) -> SavedAlert:
    return create_alert(payload)


@app.delete("/api/alerts/{alert_id}")
def alerts_delete_endpoint(alert_id: str) -> dict[str, bool]:
    removed = delete_alert(alert_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"deleted": True}


@app.get("/api/applications/stats", response_model=ApplicationStats)
def application_stats_endpoint() -> ApplicationStats:
    return application_stats(get_profile())


@app.post("/api/documents/follow-up", response_model=FollowUpResponse)
def follow_up_endpoint(payload: FollowUpRequest) -> FollowUpResponse:
    return generate_follow_up(payload, get_profile())


@app.post("/api/documents/linkedin-message", response_model=LinkedInMessageResponse)
def linkedin_message_endpoint(payload: LinkedInMessageRequest) -> LinkedInMessageResponse:
    return generate_linkedin_message(payload, get_profile())


@app.post("/api/jobs/compare", response_model=JobCompareResponse)
def compare_jobs_endpoint(payload: JobCompareRequest) -> JobCompareResponse:
    return compare_jobs(payload, get_profile())


@app.get("/api/reports/weekly", response_model=WeeklyReportResponse)
def weekly_report_endpoint() -> WeeklyReportResponse:
    return weekly_report(get_profile())


@app.get("/api/jobs/bookmarks", response_model=list[BookmarkedJob])
def bookmarks_list_endpoint() -> list[BookmarkedJob]:
    return list_bookmarks()


@app.post("/api/jobs/bookmarks", response_model=BookmarkedJob)
def bookmarks_add_endpoint(
    job: JobPosting = Body(...),
    note: str = Body(default=""),
) -> BookmarkedJob:
    return add_bookmark(job, note)


@app.delete("/api/jobs/bookmarks/{bookmark_id}")
def bookmarks_delete_endpoint(bookmark_id: str) -> dict[str, bool]:
    removed = remove_bookmark(bookmark_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"deleted": True}
