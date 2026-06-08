import re

from app.models import JobPosting


STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "or",
    "the",
    "to",
    "with",
}


def _terms(query: str) -> list[str]:
    return [
        term
        for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) > 2 and term not in STOPWORDS
    ]


def filter_relevant_jobs(jobs: list[JobPosting], query: str) -> list[JobPosting]:
    terms = _terms(query)
    if not terms:
        return jobs

    relevant: list[JobPosting] = []
    for job in jobs:
        searchable = " ".join(
            value.lower()
            for value in [
                job.title,
                job.company,
                job.location,
                job.description,
            ]
            if value
        )
        if all(term in searchable for term in terms):
            relevant.append(job)

    return relevant


def filter_jobs_by_any_term(jobs: list[JobPosting], terms: list[str]) -> list[JobPosting]:
    if not terms:
        return jobs

    normalized_terms = [term.lower() for term in terms]
    relevant: list[JobPosting] = []

    for job in jobs:
        searchable = " ".join(
            value.lower()
            for value in [
                job.title,
                job.company,
                job.location,
                job.description,
            ]
            if value
        )
        if any(term in searchable for term in normalized_terms):
            relevant.append(job)

    return relevant
