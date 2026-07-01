import json
import re
from dataclasses import dataclass

from app.models import JobPosting
from app.services.llm_adapter import LlmAdapter, MissingKeyError, extract_json_object


COUNTRY_LANGUAGES = {
    "at": ["German", "English"],
    "be": ["Dutch", "French", "English"],
    "ch": ["German", "French", "English"],
    "de": ["German", "English"],
    "gb": ["English"],
    "tr": ["Turkish", "English"],
}

STATIC_QUERY_VARIANTS = {
    "embryologist": [
        "embryologist",
        "clinical embryologist",
        "ivf embryologist",
        "embryologe",
        "klinischer embryologe",
        "embryologie",
        "embryologiste",
        "embriyolog",
    ],
    "ivf": [
        "ivf",
        "in vitro fertilization",
        "in-vitro fertilisation",
        "assisted reproductive technology",
        "art",
        "kinderwunsch",
        "reproduktionsmedizin",
        "fertility",
        "fertilite",
        "tup bebek",
    ],
    "research assistant": [
        "research assistant",
        "wissenschaftliche hilfskraft",
        "wissenschaftlicher mitarbeiter",
        "assistant de recherche",
        "onderzoeksassistent",
        "arastirma asistani",
    ],
    "laboratory": [
        "laboratory",
        "lab",
        "labor",
        "laboratoire",
        "laboratuvar",
    ],
}

NEGATIVE_TERMS = {
    "accountant",
    "accounting",
    "bartender",
    "cashier",
    "driver",
    "electrician",
    "finance",
    "marketing",
    "nurse",
    "retail",
    "sales",
    "security",
    "software",
    "warehouse",
}

SEARCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "assistant",
    "for",
    "in",
    "job",
    "jobs",
    "of",
    "or",
    "role",
    "roles",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class SearchIntelligenceResult:
    jobs: list[JobPosting]
    provider: str
    note: str


def translated_query_variants(query: str, countries: list[str], limit: int = 8) -> list[str]:
    cleaned = " ".join(query.split())
    if not cleaned:
        return [""]

    variants = _fallback_query_variants(cleaned)
    llm_variants = _llm_query_variants(cleaned, countries)
    variants = _unique([cleaned, *llm_variants, *variants])
    return variants[:limit]


def smart_filter_jobs(jobs: list[JobPosting], query: str, countries: list[str]) -> SearchIntelligenceResult:
    if not jobs or not query.strip():
        return SearchIntelligenceResult(jobs=jobs, provider="none", note="")

    llm_result = _llm_filter_jobs(jobs, query, countries)
    if llm_result is not None:
        return llm_result

    scored = []
    for job in jobs:
        score = _local_relevance_score(job, query)
        if score >= 45:
            scored.append((score, job))

    scored.sort(key=lambda item: item[0], reverse=True)
    return SearchIntelligenceResult(
        jobs=[job for _, job in scored],
        provider="local",
        note="Filtered by local semantic keyword scoring because no AI provider is available.",
    )


def _llm_query_variants(query: str, countries: list[str]) -> list[str]:
    adapter = LlmAdapter()
    if not adapter.available_providers():
        return []

    languages = _languages_for_countries(countries)
    system = (
        "You expand job-search keywords for international job boards. "
        "Return compact JSON only."
    )
    user = json.dumps(
        {
            "task": "Translate and expand the search phrase for job search.",
            "search_phrase": query,
            "languages": languages,
            "rules": [
                "Keep the original English query.",
                "Add local-language equivalents used in job titles.",
                "Prefer professional job-board phrases, not long sentences.",
                "Return at most 8 query strings.",
            ],
            "schema": {"queries": ["string"]},
        }
    )

    try:
        text, _provider = adapter.ask_default(system, user)
    except (MissingKeyError, Exception):
        return []

    data = extract_json_object(text)
    queries = data.get("queries", [])
    if not isinstance(queries, list):
        return []
    return [str(item).strip() for item in queries if str(item).strip()]


def _llm_filter_jobs(
    jobs: list[JobPosting], query: str, countries: list[str]
) -> SearchIntelligenceResult | None:
    adapter = LlmAdapter()
    if not adapter.available_providers():
        return None

    sample = [_job_payload(index, job) for index, job in enumerate(jobs[:40])]
    system = (
        "You are a strict job-search relevance filter. "
        "Keep jobs that genuinely match the user's target role or close synonyms, "
        "including translated/local-language titles. Reject unrelated industries, "
        "generic false positives, and jobs that only match location/company text. "
        "Return compact JSON only."
    )
    user = json.dumps(
        {
            "query": query,
            "countries": countries,
            "languages": _languages_for_countries(countries),
            "jobs": sample,
            "schema": {
                "matches": [
                    {
                        "id": 0,
                        "score": 0,
                        "reason": "short phrase",
                    }
                ]
            },
        }
    )

    try:
        text, provider = adapter.ask_default(system, user)
    except (MissingKeyError, Exception):
        return None

    data = extract_json_object(text)
    matches = data.get("matches", [])
    if not isinstance(matches, list):
        return None

    by_id = {index: job for index, job in enumerate(jobs[:40])}
    ranked: list[tuple[int, JobPosting]] = []
    for match in matches:
        if not isinstance(match, dict):
            continue
        try:
            job_id = int(match.get("id"))
            score = int(match.get("score", 0))
        except (TypeError, ValueError):
            continue
        if score >= 60 and job_id in by_id:
            ranked.append((score, by_id[job_id]))

    kept_ids = {id(job) for _, job in ranked}
    tail = [job for job in jobs[40:] if _local_relevance_score(job, query) >= 55]
    ranked.sort(key=lambda item: item[0], reverse=True)
    filtered = [job for _, job in ranked]
    filtered.extend(job for job in tail if id(job) not in kept_ids)

    return SearchIntelligenceResult(
        jobs=filtered,
        provider=provider,
        note=f"Filtered by {provider} relevance judging with local keyword fallback for overflow results.",
    )


def _fallback_query_variants(query: str) -> list[str]:
    normalized = query.lower()
    variants: list[str] = []

    for key, values in STATIC_QUERY_VARIANTS.items():
        if key in normalized:
            variants.extend(values)

    if not variants:
        variants.append(query)

    return variants


def _local_relevance_score(job: JobPosting, query: str) -> int:
    query_terms = _query_terms(query)
    if not query_terms:
        return 100

    title = (job.title or "").lower()
    description = (job.description or "").lower()
    company = (job.company or "").lower()
    searchable = f"{title} {description} {company}"
    expanded_terms = set(query_terms)

    for key, values in STATIC_QUERY_VARIANTS.items():
        if key in query.lower() or any(term in key for term in query_terms):
            expanded_terms.update(_query_terms(" ".join(values)))

    score = 0
    for term in query_terms:
        if term in title:
            score += 35
        elif term in searchable:
            score += 18

    for term in expanded_terms - set(query_terms):
        if term in title:
            score += 18
        elif term in searchable:
            score += 8

    if any(term in title for term in expanded_terms):
        score += 15
    if any(term in searchable for term in {"ivf", "embryo", "fertility", "reproduction", "labor", "lab"}):
        score += 10
    if any(term in searchable for term in NEGATIVE_TERMS) and not any(term in title for term in expanded_terms):
        score -= 25

    return max(0, min(score, 100))


def _query_terms(value: str) -> list[str]:
    return [
        term
        for term in re.findall(r"[a-zA-Z0-9]+", value.lower())
        if len(term) > 2 and term not in SEARCH_STOPWORDS
    ]


def _job_payload(index: int, job: JobPosting) -> dict[str, str | int | None]:
    return {
        "id": index,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": (job.description or "")[:700],
        "source": job.source,
    }


def _languages_for_countries(countries: list[str]) -> list[str]:
    languages: list[str] = []
    for country in countries:
        languages.extend(COUNTRY_LANGUAGES.get(country, ["English"]))
    return _unique(languages)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = " ".join(str(value).split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            unique.append(cleaned)
            seen.add(key)
    return unique
