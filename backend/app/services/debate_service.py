import re

import requests

from app.models import AgentOpinion, DebateRequest, DebateResponse, JobPosting, UserProfile
from app.services.llm_adapter import LlmAdapter, MissingKeyError, extract_json_object
from app.services.matching_service import rank_jobs


OPINION_SYSTEM = (
    "You are a senior career advisor. Evaluate whether the candidate should apply for the job. "
    "Return only JSON with keys: summary, recommendation, confidence, strengths, gaps. "
    "recommendation must be one of: apply, maybe, do_not_apply. confidence is 0-100. "
    "strengths and gaps are short string arrays."
)

JUDGE_SYSTEM = (
    "You are the final judge in a career-agent debate. Compare Grok and Gemini opinions, resolve "
    "disagreements, and make the final practical decision. Return only JSON with keys: summary, "
    "recommendation, confidence, strengths, gaps. recommendation must be one of: apply, maybe, do_not_apply."
)


def run_debate(payload: DebateRequest, fallback_profile: UserProfile) -> DebateResponse:
    profile = payload.profile or fallback_profile
    adapter = LlmAdapter()
    grok = _ask_provider("grok", adapter, payload, profile)
    gemini = _ask_provider("gemini", adapter, payload, profile)
    judge = _judge(adapter, payload, profile, grok, gemini)
    return DebateResponse(
        job=payload.job,
        question=payload.question,
        grok=grok,
        gemini=gemini,
        judge=judge,
    )


def fallback_opinion(provider: str, job: JobPosting, profile: UserProfile, cv_text: str = "") -> AgentOpinion:
    match = rank_jobs([job], profile, cv_text)[0]
    if match.score >= 70:
        recommendation = "apply"
    elif match.score >= 45:
        recommendation = "maybe"
    else:
        recommendation = "do_not_apply"
    return AgentOpinion(
        provider=provider,
        status="fallback",
        summary=(
            f"Heuristic review gives this role a {match.score}% fit. "
            f"Recommendation: {recommendation.replace('_', ' ')}."
        ),
        recommendation=recommendation,
        confidence=match.score,
        strengths=match.strengths,
        gaps=match.gaps,
    )


def _ask_provider(
    provider: str,
    adapter: LlmAdapter,
    payload: DebateRequest,
    profile: UserProfile,
) -> AgentOpinion:
    prompt = _candidate_job_prompt(payload, profile)
    try:
        if provider == "grok":
            raw = adapter.ask_grok(OPINION_SYSTEM, prompt)
            return _parse_opinion(provider, adapter.grok_model, raw)
        raw = adapter.ask_gemini(OPINION_SYSTEM, prompt)
        return _parse_opinion(provider, adapter.gemini_model, raw)
    except MissingKeyError as exc:
        opinion = fallback_opinion(provider, payload.job, profile, payload.cv_text)
        opinion.status = "missing_key"
        opinion.error = str(exc)
        return opinion
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        opinion = fallback_opinion(provider, payload.job, profile, payload.cv_text)
        opinion.status = "error"
        opinion.error = str(exc)
        return opinion


def _judge(
    adapter: LlmAdapter,
    payload: DebateRequest,
    profile: UserProfile,
    grok: AgentOpinion,
    gemini: AgentOpinion,
) -> AgentOpinion:
    user = (
        f"{_candidate_job_prompt(payload, profile)}\n\n"
        f"Grok opinion:\n{grok.model_dump()}\n\n"
        f"Gemini opinion:\n{gemini.model_dump()}\n\n"
        "Make the final decision for the user."
    )
    try:
        if adapter.judge_provider == "grok":
            raw = adapter.ask_grok(JUDGE_SYSTEM, user)
            return _parse_opinion("judge", adapter.grok_model, raw)
        raw = adapter.ask_gemini(JUDGE_SYSTEM, user)
        return _parse_opinion("judge", adapter.gemini_model, raw)
    except Exception as exc:
        return _fallback_judge(payload.job, profile, payload.cv_text, grok, gemini, str(exc))


def _fallback_judge(
    job: JobPosting,
    profile: UserProfile,
    cv_text: str,
    grok: AgentOpinion,
    gemini: AgentOpinion,
    error: str,
) -> AgentOpinion:
    opinions = [grok, gemini]
    apply_votes = sum(1 for opinion in opinions if opinion.recommendation == "apply")
    do_not_votes = sum(1 for opinion in opinions if opinion.recommendation == "do_not_apply")
    average_confidence = round(sum(opinion.confidence for opinion in opinions) / max(1, len(opinions)))
    heuristic = fallback_opinion("judge", job, profile, cv_text)
    if apply_votes > do_not_votes:
        recommendation = "apply"
    elif do_not_votes > apply_votes:
        recommendation = "do_not_apply"
    else:
        recommendation = heuristic.recommendation
    strengths = _dedupe(grok.strengths + gemini.strengths + heuristic.strengths)[:6]
    gaps = _dedupe(grok.gaps + gemini.gaps + heuristic.gaps)[:6]
    return AgentOpinion(
        provider="judge",
        status="fallback",
        summary=(
            "I combined the available agent opinions with the local match score because the judge "
            "model was unavailable. "
            f"Final decision: {recommendation.replace('_', ' ')}."
        ),
        recommendation=recommendation,
        confidence=max(heuristic.confidence, average_confidence),
        strengths=strengths,
        gaps=gaps,
        error=error,
    )


def _parse_opinion(provider: str, model: str, raw: str) -> AgentOpinion:
    data = extract_json_object(raw)
    recommendation = str(data.get("recommendation", "maybe")).strip().lower()
    if recommendation not in {"apply", "maybe", "do_not_apply"}:
        recommendation = "maybe"
    confidence = _bounded_int(data.get("confidence", 50))
    return AgentOpinion(
        provider=provider,
        model=model,
        status="ok",
        summary=str(data.get("summary") or raw[:600]),
        recommendation=recommendation,
        confidence=confidence,
        strengths=_clean_list(data.get("strengths")),
        gaps=_clean_list(data.get("gaps")),
        raw=raw,
    )


def _candidate_job_prompt(payload: DebateRequest, profile: UserProfile) -> str:
    job = payload.job
    return (
        f"Question: {payload.question}\n\n"
        f"Candidate profile:\n"
        f"Skills: {', '.join(profile.skills) or 'unknown'}\n"
        f"Languages: {', '.join(profile.languages) or 'unknown'}\n"
        f"Target roles: {', '.join(profile.target_roles) or 'unknown'}\n"
        f"Preferred locations: {', '.join(profile.preferred_locations) or 'unknown'}\n"
        f"CV summary/text: {(payload.cv_text or profile.cv_summary or 'unknown')[:6000]}\n\n"
        f"Job:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company or 'unknown'}\n"
        f"Location: {job.location or 'unknown'}\n"
        f"Description: {(job.description or '')[:6000]}\n"
        f"Salary: {job.salary_text or 'unknown'}\n"
        f"Apply URL: {job.apply_url or job.source_url or 'unknown'}"
    )


def _bounded_int(value) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 50


def _clean_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:8]


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = re.sub(r"\s+", " ", item.strip().lower())
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result
