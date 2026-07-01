"""Extra career services: follow-up emails, linkedin messages, job comparison,
weekly reports, application stats, and saved alerts."""

from collections import Counter
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.models import (
    AlertCreate,
    ApplicationStats,
    BookmarkedJob,
    FollowUpRequest,
    FollowUpResponse,
    JobCompareRequest,
    JobCompareResponse,
    JobPosting,
    LinkedInMessageRequest,
    LinkedInMessageResponse,
    SavedAlert,
    UserProfile,
    WeeklyReportResponse,
)
from app.services.storage import JsonStore
from app.services.serialization import model_dump


ALERTS_STORE = JsonStore("alerts.json", [])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Application Stats ---

def application_stats(profile: UserProfile) -> ApplicationStats:
    apps = profile.applications
    total = len(apps)
    counts = Counter(a.status for a in apps)
    interview_or_applied = counts.get("interview", 0) + counts.get("applied", 0)
    rate = round(interview_or_applied / total * 100, 1) if total else 0.0
    return ApplicationStats(
        total=total,
        saved=counts.get("saved", 0),
        prepared=counts.get("prepared", 0),
        applied=counts.get("applied", 0),
        interview=counts.get("interview", 0),
        rejected=counts.get("rejected", 0),
        conversion_rate=rate,
    )


# --- Follow-Up Email ---

def generate_follow_up(payload: FollowUpRequest, profile: UserProfile) -> FollowUpResponse:
    role = payload.job.title if payload.job else "the role"
    company = payload.job.company if payload.job else "the company"
    name = payload.interviewer_name or "Hiring Manager"
    skills = ", ".join(profile.skills[:5]) or "my relevant experience"

    subject = f"Thank you — {role} at {company}"
    body = (
        f"Dear {name},\n\n"
        f"Thank you for taking the time to discuss the {role} position"
        f"{' on ' + payload.interview_date if payload.interview_date else ''}. "
        f"I enjoyed learning more about {company} and the team.\n\n"
        f"Our conversation reinforced my enthusiasm for this opportunity. "
        f"My background in {skills} aligns well with what you described, "
        f"and I am confident I can contribute meaningfully from day one.\n\n"
        f"Please do not hesitate to reach out if you need any additional information. "
        f"I look forward to hearing from you.\n\n"
        f"Best regards"
    )
    return FollowUpResponse(subject=subject, body=body)


# --- LinkedIn Message ---

def generate_linkedin_message(payload: LinkedInMessageRequest, profile: UserProfile) -> LinkedInMessageResponse:
    person = payload.target_person or "there"
    company = payload.target_company or "your company"
    role = payload.target_role or (profile.target_roles[0] if profile.target_roles else "opportunities")
    skills = ", ".join(profile.skills[:4]) or "relevant experience"

    templates = {
        "networking": (
            f"Hi {person},\n\n"
            f"I came across your profile and was impressed by your work at {company}. "
            f"I am exploring {role} roles and would value a brief chat about your experience. "
            f"My background includes {skills}.\n\n"
            f"Would you be open to a short conversation? Thank you!"
        ),
        "referral": (
            f"Hi {person},\n\n"
            f"I noticed {company} has an opening for {role} and your profile suggests "
            f"you might be connected to the team. I bring {skills} and believe I could "
            f"be a strong fit. Would you be willing to share my profile or introduce me? "
            f"Happy to share my CV. Thank you!"
        ),
        "cold_outreach": (
            f"Hi {person},\n\n"
            f"I am a professional with experience in {skills}, currently exploring "
            f"{role} opportunities. I admire what {company} is doing and would love "
            f"to discuss how I might contribute. Would you be open to connecting?"
        ),
        "follow_up": (
            f"Hi {person},\n\n"
            f"Thank you for connecting. I wanted to follow up on my interest in "
            f"{role} at {company}. I would appreciate any insights you could share "
            f"about the team or hiring process. Looking forward to hearing from you!"
        ),
    }
    message = templates.get(payload.purpose, templates["networking"])
    return LinkedInMessageResponse(message=message, character_count=len(message))


# --- Job Comparison ---

def compare_jobs(payload: JobCompareRequest, profile: UserProfile) -> JobCompareResponse:
    comparison = []
    user_skills = {s.lower() for s in profile.skills}

    for job in payload.jobs:
        desc_lower = (job.description or "").lower()
        matching_skills = [s for s in profile.skills if s.lower() in desc_lower]
        salary_info = job.salary_text or ""
        if not salary_info and (job.salary_min or job.salary_max):
            parts = []
            if job.salary_min:
                parts.append(f"{job.salary_min:,.0f}")
            if job.salary_max:
                parts.append(f"{job.salary_max:,.0f}")
            salary_info = " - ".join(parts) + f" {job.currency or 'EUR'}"

        comparison.append({
            "title": job.title,
            "company": job.company or "Unknown",
            "location": job.location or "Not specified",
            "salary": salary_info or "Not disclosed",
            "remote": "Yes" if job.is_remote else "No",
            "matching_skills": matching_skills,
            "skill_match_count": len(matching_skills),
            "source": job.source,
        })

    # Sort by skill match count descending
    comparison.sort(key=lambda c: c["skill_match_count"], reverse=True)
    best = comparison[0] if comparison else {}
    recommendation = (
        f"Based on your profile, '{best.get('title', '')}' at {best.get('company', '')} "
        f"has the strongest skill overlap ({best.get('skill_match_count', 0)} matching skills)."
        if best else "Unable to determine a recommendation."
    )
    return JobCompareResponse(comparison=comparison, recommendation=recommendation)


# --- Weekly Report ---

def weekly_report(profile: UserProfile) -> WeeklyReportResponse:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    period = f"{week_ago.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"

    recent = [
        a for a in profile.applications
        if a.created_at and a.created_at >= week_ago.isoformat()
    ]
    status_counts = Counter(a.status for a in recent)
    roles = [a.job.title for a in recent if a.job.title]
    top_roles = [role for role, _ in Counter(roles).most_common(5)]

    total = len(profile.applications)
    summary = (
        f"This week you created {len(recent)} new application(s) out of {total} total. "
        f"{'Top roles: ' + ', '.join(top_roles) + '.' if top_roles else 'No new roles this week.'}"
    )
    return WeeklyReportResponse(
        period=period,
        applications_created=len(recent),
        applications_by_status=dict(status_counts),
        top_roles=top_roles,
        summary=summary,
    )


# --- Saved Alerts ---

def list_alerts() -> list[SavedAlert]:
    return [SavedAlert(**item) for item in ALERTS_STORE.read()]


def create_alert(payload: AlertCreate) -> SavedAlert:
    alerts = list_alerts()
    alert = SavedAlert(
        id=str(uuid4()),
        query=payload.query,
        location=payload.location,
        country=payload.country,
        include_remote=payload.include_remote,
        sources=payload.sources,
        created_at=_now_iso(),
    )
    alerts.insert(0, alert)
    ALERTS_STORE.write([model_dump(a) for a in alerts])
    return alert


def delete_alert(alert_id: str) -> bool:
    alerts = list_alerts()
    filtered = [a for a in alerts if a.id != alert_id]
    if len(filtered) == len(alerts):
        return False
    ALERTS_STORE.write([model_dump(a) for a in filtered])
    return True
