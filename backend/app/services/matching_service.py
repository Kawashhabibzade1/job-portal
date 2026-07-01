import re

from app.models import JobMatch, JobPosting, UserProfile


IMPORTANT_TERMS = {
    "python",
    "javascript",
    "typescript",
    "react",
    "fastapi",
    "sql",
    "german",
    "english",
    "research",
    "laboratory",
    "ivf",
    "embryology",
    "remote",
    "manager",
    "analysis",
}


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z][a-zA-Z+#.-]{1,}", text.lower()) if len(token) > 2}


def _job_text(job: JobPosting) -> str:
    return " ".join(
        str(value or "")
        for value in [job.title, job.company, job.location, job.description, job.salary_text]
    )


def rank_jobs(jobs: list[JobPosting], profile: UserProfile, cv_text: str = "") -> list[JobMatch]:
    profile_terms = _tokens(" ".join(profile.skills + profile.languages + profile.target_roles + [profile.cv_summary, cv_text]))
    if not profile_terms:
        profile_terms = _tokens(" ".join(profile.target_roles + [cv_text]))

    matches: list[JobMatch] = []
    for job in jobs:
        job_terms = _tokens(_job_text(job))
        overlap = sorted(profile_terms & job_terms)
        important_overlap = [term for term in overlap if term in IMPORTANT_TERMS]
        score = min(95, 35 + len(overlap) * 4 + len(important_overlap) * 6)
        if not overlap:
            score = 30
        gaps = sorted((job_terms & IMPORTANT_TERMS) - profile_terms)[:5]
        if score >= 75:
            recommendation = "strong"
        elif score >= 50:
            recommendation = "possible"
        else:
            recommendation = "stretch"
        matches.append(
            JobMatch(
                job=job,
                score=score,
                recommendation=recommendation,
                strengths=[term.title() for term in overlap[:6]] or ["Relevant role context"],
                gaps=[term.title() for term in gaps] or [],
            )
        )
    return sorted(matches, key=lambda item: item.score, reverse=True)
