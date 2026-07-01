from datetime import datetime, timezone
from uuid import uuid4

from app.models import CoverLetterRequest, CoverLetterResponse, JobPosting, UserProfile
from app.services.serialization import model_dump
from app.services.storage import JsonStore


COVER_LETTER_STORE = JsonStore("cover_letters.json", [])


def _profile_line(profile: UserProfile) -> str:
    skills = ", ".join(profile.skills[:6]) or "relevant experience"
    roles = ", ".join(profile.target_roles[:3]) or "this role"
    return f"My background combines {skills}, and I am targeting {roles}."


def _english_letter(job: JobPosting, profile: UserProfile, tone: str) -> str:
    company = job.company or "your team"
    return (
        f"Dear Hiring Team,\n\n"
        f"I am writing to apply for the {job.title} position at {company}. "
        f"{_profile_line(profile)} The role stands out to me because it matches both my current skills "
        f"and the direction I want to take next.\n\n"
        f"I would bring a practical, careful, and collaborative approach to the work. "
        f"Based on the job details, I can contribute quickly while continuing to close any remaining skill gaps.\n\n"
        f"Thank you for considering my application. I would welcome the opportunity to discuss how my experience "
        f"can support {company}.\n\n"
        f"Sincerely,\n"
        f"Applicant"
    )


def _german_letter(job: JobPosting, profile: UserProfile, tone: str) -> str:
    company = job.company or "Ihr Team"
    skills = ", ".join(profile.skills[:6]) or "relevante Erfahrung"
    return (
        f"Sehr geehrte Damen und Herren,\n\n"
        f"hiermit bewerbe ich mich auf die Position {job.title} bei {company}. "
        f"Mein Profil verbindet {skills} mit einer klaren Motivation fuer diese Aufgabe.\n\n"
        f"Ich arbeite strukturiert, sorgfaeltig und teamorientiert. Die ausgeschriebene Position passt gut zu "
        f"meinen bisherigen Erfahrungen und zu meinen naechsten beruflichen Zielen.\n\n"
        f"Vielen Dank fuer die Pruefung meiner Unterlagen. Ich freue mich ueber die Gelegenheit, meine Eignung "
        f"in einem Gespraech naeher zu erlaeutern.\n\n"
        f"Mit freundlichen Gruessen\n"
        f"Bewerber/in"
    )


def create_cover_letter(payload: CoverLetterRequest, fallback_profile: UserProfile) -> CoverLetterResponse:
    profile = payload.profile or fallback_profile
    text = (
        _german_letter(payload.job, profile, payload.tone)
        if payload.language == "de"
        else _english_letter(payload.job, profile, payload.tone)
    )
    response = CoverLetterResponse(
        id=str(uuid4()),
        language=payload.language,
        text=text,
        export_ids={},
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    letters = COVER_LETTER_STORE.read()
    letters.insert(0, model_dump(response))
    COVER_LETTER_STORE.write(letters)
    return response
