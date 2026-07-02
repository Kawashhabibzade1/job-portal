from typing import Any, Literal, Optional

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    source: str
    sources: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    apply_url: Optional[str] = None
    date_posted: Optional[str] = None
    scraped_at: Optional[str] = None
    salary_text: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    is_remote: Optional[bool] = None
    country: Optional[str] = None


class JobSearchResponse(BaseModel):
    query: str = ""
    location: str = ""
    country: str = "de"
    count: int
    jobs: list[JobPosting]
    sources: dict[str, int] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
    search_queries: list[str] = Field(default_factory=list)
    ai_filter_provider: str = "none"
    ai_filter_note: str = ""


class ApplicationRecord(BaseModel):
    id: str
    job: JobPosting
    status: Literal["saved", "prepared", "applied", "rejected", "interview"] = "saved"
    notes: str = ""
    cover_letter_id: Optional[str] = None
    created_at: str
    updated_at: str


class UserProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    cv_summary: str = ""
    documents: list[str] = Field(default_factory=list)
    applications: list[ApplicationRecord] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    skills: list[str] | None = None
    preferred_locations: list[str] | None = None
    languages: list[str] | None = None
    target_roles: list[str] | None = None
    cv_summary: str | None = None


class UploadedDocument(BaseModel):
    id: str
    filename: str
    content_type: str = ""
    document_type: Literal["cv", "job_description", "certificate", "other"] = "other"
    text: str = ""
    status: Literal["processed", "partial", "unsupported", "error"] = "processed"
    message: str = ""
    created_at: str


class DocumentUpdate(BaseModel):
    document_type: Literal["cv", "job_description", "certificate", "other"] | None = None
    text: str | None = None


class ChatAttachment(BaseModel):
    document_id: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    attachments: list[ChatAttachment] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class ChatAction(BaseModel):
    type: str
    label: str
    status: Literal["completed", "needs_confirmation", "failed", "info"] = "completed"
    data: dict[str, Any] = Field(default_factory=dict)


class ChatNavigation(BaseModel):
    view: Literal["chat", "jobs", "profile", "applications", "documents"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    actions: list[ChatAction] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    navigation: Optional[ChatNavigation] = None


class JobMatch(BaseModel):
    job: JobPosting
    score: int
    recommendation: Literal["strong", "possible", "stretch"]
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class JobMatchRequest(BaseModel):
    jobs: list[JobPosting] = Field(default_factory=list)
    query: str = ""
    location: str = ""
    country: str = "de"
    sources: list[str] = Field(default_factory=list)
    include_remote: bool = False
    cv_text: str = ""


class JobMatchResponse(BaseModel):
    count: int
    matches: list[JobMatch]


class DebateRequest(BaseModel):
    job: JobPosting
    question: str = "Can I apply?"
    cv_text: str = ""
    profile: Optional[UserProfile] = None


class AgentOpinion(BaseModel):
    provider: Literal["grok", "gemini", "judge", "system"]
    model: str = ""
    status: Literal["ok", "missing_key", "error", "fallback"] = "ok"
    summary: str = ""
    recommendation: Literal["apply", "maybe", "do_not_apply"] = "maybe"
    confidence: int = 50
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    raw: str = ""
    error: str = ""


class DebateResponse(BaseModel):
    job: JobPosting
    question: str
    grok: AgentOpinion
    gemini: AgentOpinion
    judge: AgentOpinion


class CoverLetterRequest(BaseModel):
    job: JobPosting
    language: Literal["en", "de"] = "en"
    tone: str = "professional"
    profile: Optional[UserProfile] = None


class CoverLetterResponse(BaseModel):
    id: str
    language: Literal["en", "de"]
    text: str
    export_ids: dict[str, str] = Field(default_factory=dict)
    created_at: str


class ApplicationCreate(BaseModel):
    job: JobPosting
    status: Literal["saved", "prepared", "applied", "rejected", "interview"] = "saved"
    notes: str = ""
    cover_letter_id: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Literal["saved", "prepared", "applied", "rejected", "interview"] | None = None
    notes: str | None = None
    cover_letter_id: Optional[str] = None


class GeneratedFile(BaseModel):
    id: str
    filename: str
    path: str
    mime_type: str
    kind: str
    created_at: str


class ExportRequest(BaseModel):
    format: Literal["pdf", "docx", "txt"]
    cover_letter_id: Optional[str] = None
    text: str = ""
    filename: str = "CoverLetter"


class ApplicationPackageRequest(BaseModel):
    application_name: str
    job: Optional[JobPosting] = None
    cover_letter_id: Optional[str] = None
    certificate_document_ids: list[str] = Field(default_factory=list)
    cv_document_id: Optional[str] = None


class ApplicationPackageResponse(BaseModel):
    folder: str
    files: list[GeneratedFile]
    summary: str


class CvImproveRequest(BaseModel):
    cv_text: str = ""
    target_role: str = ""
    job: Optional[JobPosting] = None


class CvImproveResponse(BaseModel):
    improved_text: str
    changes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class CvSuggestion(BaseModel):
    section: str
    issue: str
    recommendation: str
    priority: Literal["high", "medium", "low"] = "medium"


class CvSuggestionsResponse(BaseModel):
    suggestions: list[CvSuggestion] = Field(default_factory=list)
    overall_score: int = 0
    summary: str = ""


class ProfileSummaryRequest(BaseModel):
    document_id: Optional[str] = None
    cv_text: str = ""


class ArtifactRoadmapRequest(BaseModel):
    job: JobPosting
    target_country: str = ""
    languages: list[str] = Field(default_factory=list)
    profile: Optional["UserProfile"] = None


class ArtifactRoadmapStep(BaseModel):
    category: str
    title: str
    description: str
    required: bool = True
    link: str = ""


class ArtifactRoadmapResponse(BaseModel):
    job_title: str
    company: str = ""
    country: str = ""
    steps: list[ArtifactRoadmapStep] = Field(default_factory=list)
    documents_needed: list[str] = Field(default_factory=list)
    visa_info: str = ""
    language_requirements: str = ""
    timeline_weeks: int = 4
    tips: list[str] = Field(default_factory=list)


class CvCompareRequest(BaseModel):
    original_text: str
    revised_text: str


class CvCompareResponse(BaseModel):
    added_keywords: list[str] = Field(default_factory=list)
    removed_keywords: list[str] = Field(default_factory=list)
    summary: str


class InterviewPrepRequest(BaseModel):
    role: str
    job: Optional[JobPosting] = None


class InterviewPrepResponse(BaseModel):
    technical_questions: list[str] = Field(default_factory=list)
    behavioral_questions: list[str] = Field(default_factory=list)
    regulatory_questions: list[str] = Field(default_factory=list)
    answer_strategy: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    application_id: Optional[str] = None
    rejection_text: str = ""
    job: Optional[JobPosting] = None


class FeedbackResponse(BaseModel):
    likely_reasons: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class RoadmapRequest(BaseModel):
    target_role: str
    job: Optional[JobPosting] = None


class RoadmapResponse(BaseModel):
    missing_skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)


class PdfMergeRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    generated_file_ids: list[str] = Field(default_factory=list)
    filename: str = "MergedDocuments"


class PdfOrganizeRequest(BaseModel):
    document_id: Optional[str] = None
    generated_file_id: Optional[str] = None
    filename: str = "OrganizedDocument"
    page_order: list[int] = Field(default_factory=list)
    delete_pages: list[int] = Field(default_factory=list)
    rotate_pages: dict[int, int] = Field(default_factory=dict)


class PdfOperationResponse(BaseModel):
    file: GeneratedFile


class ApplyAutomationRequest(BaseModel):
    job: JobPosting
    profile: Optional[UserProfile] = None
    confirm_submit: bool = False


class ApplyAutomationResponse(BaseModel):
    status: Literal["prepared", "needs_confirmation", "submitted", "blocked"]
    message: str
    fields: dict[str, str] = Field(default_factory=dict)
    apply_url: str = ""
    confirmation_required: bool = True


# --- New feature models ---


class SalaryBucket(BaseModel):
    role: str
    country: str
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    avg_salary: Optional[float] = None
    currency: str = "EUR"
    sample_count: int = 0


class SalaryInsightsRequest(BaseModel):
    jobs: list[JobPosting] = Field(default_factory=list)
    query: str = ""
    country: str = "de"


class SalaryInsightsResponse(BaseModel):
    buckets: list[SalaryBucket] = Field(default_factory=list)
    overall_min: Optional[float] = None
    overall_max: Optional[float] = None
    overall_avg: Optional[float] = None
    sample_count: int = 0
    note: str = ""


class SavedAlert(BaseModel):
    id: str
    query: str
    location: str = ""
    country: str = "de"
    include_remote: bool = False
    sources: list[str] = Field(default_factory=list)
    created_at: str


class AlertCreate(BaseModel):
    query: str
    location: str = ""
    country: str = "de"
    include_remote: bool = False
    sources: list[str] = Field(default_factory=list)


class ApplicationStats(BaseModel):
    total: int = 0
    saved: int = 0
    prepared: int = 0
    applied: int = 0
    interview: int = 0
    rejected: int = 0
    conversion_rate: float = 0.0


class FollowUpRequest(BaseModel):
    job: Optional[JobPosting] = None
    interviewer_name: str = ""
    interview_date: str = ""
    tone: str = "professional"


class FollowUpResponse(BaseModel):
    subject: str
    body: str


class LinkedInMessageRequest(BaseModel):
    target_company: str = ""
    target_person: str = ""
    target_role: str = ""
    purpose: Literal["networking", "referral", "cold_outreach", "follow_up"] = "networking"


class LinkedInMessageResponse(BaseModel):
    message: str
    character_count: int = 0


class JobCompareRequest(BaseModel):
    jobs: list[JobPosting] = Field(min_length=2, max_length=5)


class JobCompareResponse(BaseModel):
    comparison: list[dict[str, Any]] = Field(default_factory=list)
    recommendation: str = ""


class WeeklyReportResponse(BaseModel):
    period: str
    applications_created: int = 0
    applications_by_status: dict[str, int] = Field(default_factory=dict)
    top_roles: list[str] = Field(default_factory=list)
    summary: str = ""


class BookmarkedJob(BaseModel):
    id: str
    job: JobPosting
    note: str = ""
    created_at: str
