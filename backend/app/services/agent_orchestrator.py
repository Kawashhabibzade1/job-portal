import json
import re
from uuid import uuid4

from app.models import (
    ApplicationCreate,
    ChatAction,
    ChatNavigation,
    ChatRequest,
    ChatResponse,
    CoverLetterRequest,
    CvImproveRequest,
    FeedbackRequest,
    InterviewPrepRequest,
    RoadmapRequest,
    DebateRequest,
    JobPosting,
)
from app.services.career_tools import analyze_feedback, build_roadmap, improve_cv, interview_prep
from app.services.debate_service import run_debate
from app.services.document_builder import create_cover_letter
from app.services.document_service import get_document
from app.services.llm_adapter import LlmAdapter
from app.services.matching_service import rank_jobs
from app.services.profile_service import create_application, get_profile
from app.services.serialization import model_dump


SEARCH_WORDS = {"find", "search", "jobs", "roles", "vacancies", "stellen", "job"}
MATCH_WORDS = {"chance", "chances", "match", "fit", "compare", "rank", "best", "eligibility"}
COVER_WORDS = {"cover", "letter", "anschreiben", "bewerbungsschreiben"}
APPLY_WORDS = {"apply", "submit", "application", "bewerben", "send"}
APPLY_QUESTION_WORDS = {"can", "should", "could", "eligible", "eligibility", "chance", "chances"}
PROFILE_WORDS = {"cv", "resume", "profile", "skills", "lebenslauf"}
TRACKER_WORDS = {"tracker", "applications", "applied", "rejected", "interview"}
IMPROVE_WORDS = {"improve", "rewrite", "enhance", "optimize"}
INTERVIEW_WORDS = {"interview", "prepare", "questions"}
ROADMAP_WORDS = {"roadmap", "certification", "certifications", "gap", "gaps", "plan"}
FEEDBACK_WORDS = {"rejected", "rejection", "feedback", "why"}
CAREER_ADVICE_WORDS = {
    "field",
    "fields",
    "career",
    "work",
    "according",
    "experience",
    "think",
    "suitable",
    "path",
    "paths",
}

GENERAL_SYSTEM = (
    "You are the AI chat inside a job-search and application website. Behave like a capable LLM chat, "
    "not like a menu. You can discuss career strategy, improve prompts, explain website features, "
    "search jobs, rank jobs against the user's skills, draft cover letters, and prepare application records. "
    "When platform tools have already run, explain the result naturally and suggest the next useful action. "
    "Do not repeat the same generic option list unless the user asks for options. Do not claim you submitted "
    "applications or changed external job portals; final submission always requires user confirmation."
)


def classify_intent(message: str) -> str:
    tokens = set(re.findall(r"[a-zA-Z]+", message.lower()))
    if tokens & COVER_WORDS:
        return "cover_letter"
    if tokens & CAREER_ADVICE_WORDS and tokens & {"career", "experience", "field", "fields", "path", "paths", "work"}:
        return "career_advice"
    if tokens & SEARCH_WORDS and (
        tokens & PROFILE_WORDS
        or "skill" in tokens
        or "skills" in tokens
        or re.search(r"\baccording to\b|\bbased on\b|\bfor me\b|\bmy profile\b", message, re.I)
    ):
        return "search"
    if tokens & IMPROVE_WORDS and tokens & {"cv", "resume"}:
        return "cv_improve"
    if tokens & INTERVIEW_WORDS and "interview" in tokens:
        return "interview"
    if tokens & ROADMAP_WORDS:
        return "roadmap"
    if tokens & FEEDBACK_WORDS and tokens & {"rejected", "rejection", "why"}:
        return "feedback"
    if tokens & APPLY_WORDS:
        return "match" if tokens & APPLY_QUESTION_WORDS else "apply"
    if tokens & TRACKER_WORDS:
        return "tracker"
    if tokens & MATCH_WORDS:
        return "match"
    if tokens & PROFILE_WORDS:
        return "profile"
    if tokens & SEARCH_WORDS:
        return "search"
    return "general"


def _search_terms(message: str) -> tuple[str, str]:
    cleaned = re.sub(r"\b(find|search|show|me|jobs|roles|vacancies|for|in|near)\b", " ", message, flags=re.I)
    parts = [part.strip(" ,.") for part in re.split(r"\bin\b|\bnear\b", cleaned, flags=re.I) if part.strip()]
    query = parts[0] if parts else message
    location = parts[1] if len(parts) > 1 else ""
    return query.strip() or "developer", location.strip()


def _is_profile_search(message: str) -> bool:
    return bool(
        re.search(
            r"\b(my profile|my skills|my cv|my resume|according to|based on|for me|suitable)\b",
            message,
            flags=re.I,
        )
    )


def _profile_search_terms(profile, fallback_message: str = "") -> tuple[str, str]:
    priority_terms = [
        *profile.target_roles,
        *profile.skills,
    ]
    useful_terms = [
        term
        for term in priority_terms
        if term and len(term.strip()) > 2 and term.lower() not in {"english", "german", "deutsch"}
    ]
    query = " ".join(useful_terms[:4]).strip()
    if not query:
        query, _ = _search_terms(fallback_message)
    location = profile.preferred_locations[0] if profile.preferred_locations else ""
    return query or "developer", location


def _conversation_context(request: ChatRequest) -> str:
    raw_messages = request.context.get("messages") or []
    if not isinstance(raw_messages, list):
        return ""
    lines = []
    for item in raw_messages[-8:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            lines.append(f"{role}: {str(content)[:1200]}")
    return "\n".join(lines)


def _context_jobs(request: ChatRequest) -> list[JobPosting]:
    raw_jobs = request.context.get("jobs") or []
    jobs = []
    for item in raw_jobs:
        try:
            jobs.append(JobPosting(**item))
        except Exception:
            continue
    return jobs


def _attachment_text(request: ChatRequest) -> str:
    texts = []
    for attachment in request.attachments:
        document = get_document(attachment.document_id)
        if document and document.text:
            texts.append(document.text)
    return "\n".join(texts)


def handle_chat(request: ChatRequest, search_callable) -> ChatResponse:
    conversation_id = request.conversation_id or str(uuid4())
    intent = classify_intent(request.message)
    profile = get_profile()
    adapter = LlmAdapter()
    actions: list[ChatAction] = []
    suggestions = ["Find jobs for my profile", "Improve my CV", "Create a cover letter"]
    navigation = None
    message = ""

    if intent == "search":
        query, location = (
            _profile_search_terms(profile, request.message)
            if _is_profile_search(request.message)
            else _search_terms(request.message)
        )
        result = search_callable(query=query, location=location, country="all", sources=None, include_remote=True)
        actions.append(
            ChatAction(
                type="job_search",
                label=f"Found {result.count} jobs for {query}",
                data={"result": model_dump(result)},
            )
        )
        navigation = ChatNavigation(view="jobs", payload={"result": model_dump(result)})
        fallback = f"I found {result.count} jobs for {query}. I opened the job dashboard so you can review them."
        message = _tool_llm_reply(
            adapter,
            request,
            profile,
            intent="job_search",
            tool_summary={
                "query": query,
                "location": location,
                "count": result.count,
                "top_jobs": [
                    {
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "source": job.source,
                    }
                    for job in result.jobs[:5]
                ],
            },
            fallback=fallback,
        )
        suggestions = ["Rank these jobs against my CV", "Save the best role", "Create a cover letter"]

    elif intent == "match":
        jobs = _context_jobs(request)
        if not jobs:
            query, location = _search_terms(request.message)
            result = search_callable(query=query, location=location, country="all", sources=None, include_remote=True)
            jobs = result.jobs
            actions.append(ChatAction(type="job_search", label=f"Searched {result.count} jobs to rank", data={"result": model_dump(result)}))
        matches = rank_jobs(jobs, profile, _attachment_text(request))
        actions.append(ChatAction(type="job_match", label=f"Ranked {len(matches)} jobs", data={"matches": [model_dump(item) for item in matches[:10]]}))
        navigation = ChatNavigation(view="jobs", payload={"matches": [model_dump(item) for item in matches[:10]]})
        top = matches[0] if matches else None
        if top:
            debate = run_debate(
                DebateRequest(
                    job=top.job,
                    question=request.message,
                    cv_text=_attachment_text(request),
                    profile=profile,
                ),
                profile,
            )
            actions.append(
                ChatAction(
                    type="agent_debate",
                    label="Grok and Gemini debated the top job; Judge made the final call",
                    data={"debate": model_dump(debate)},
                )
            )
            message = (
                f"Your strongest match is {top.job.title} with a {top.score}% fit. "
                f"Judge decision: {debate.judge.recommendation.replace('_', ' ')} "
                f"({debate.judge.confidence}% confidence). {debate.judge.summary}"
            )
        else:
            message = "I need jobs or a search target before I can rank your fit."
        suggestions = ["Explain the top match", "Write a cover letter", "Track this application"]

    elif intent == "cover_letter":
        jobs = _context_jobs(request)
        if not jobs:
            query, location = (
                _profile_search_terms(profile, request.message)
                if _is_profile_search(request.message) or not _search_terms(request.message)[0]
                else _search_terms(request.message)
            )
            result = search_callable(query=query, location=location, country="all", sources=None, include_remote=True)
            jobs = result.jobs
            actions.append(
                ChatAction(
                    type="job_search",
                    label=f"Found {result.count} jobs before drafting",
                    data={"result": model_dump(result)},
                )
            )
            if not jobs:
                message = _tool_llm_reply(
                    adapter,
                    request,
                    profile,
                    intent="cover_letter_no_job",
                    tool_summary={"query": query, "location": location, "count": result.count},
                    fallback=(
                        "I searched first, but I could not find a job to tailor the cover letter to. "
                        "Try a more specific role or location."
                    ),
                )
                navigation = ChatNavigation(view="jobs", payload={"result": model_dump(result)})
            else:
                matches = rank_jobs(jobs, profile, _attachment_text(request))
                selected_job = matches[0].job if matches else jobs[0]
                actions.append(
                    ChatAction(
                        type="job_match",
                        label=f"Selected best match from {len(jobs)} jobs",
                        data={"matches": [model_dump(item) for item in matches[:10]]},
                    )
                )
                language = "de" if re.search(r"\bgerman\b|deutsch|anschreiben", request.message, re.I) else "en"
                letter = create_cover_letter(
                    payload=CoverLetterRequest(
                        job=selected_job,
                        language=language,
                        tone="professional",
                        profile=profile,
                    ),
                    fallback_profile=profile,
                )
                actions.append(ChatAction(type="cover_letter", label="Created cover letter draft", data={"cover_letter": model_dump(letter)}))
                navigation = ChatNavigation(
                    view="documents",
                    payload={"cover_letter": model_dump(letter), "result": model_dump(result)},
                )
                message = _tool_llm_reply(
                    adapter,
                    request,
                    profile,
                    intent="cover_letter_auto",
                    tool_summary={
                        "searched_query": query,
                        "jobs_found": result.count,
                        "selected_job": {
                            "title": selected_job.title,
                            "company": selected_job.company,
                            "location": selected_job.location,
                        },
                        "letter_preview": letter.text[:1200],
                    },
                    fallback=(
                        f"I searched for {query}, selected {selected_job.title}, and drafted a tailored cover letter. "
                        "Review it in Documents before using it."
                    ),
                )
                suggestions = ["Make it more concise", "Translate it to German", "Prepare application package"]
        else:
            language = "de" if re.search(r"\bgerman\b|deutsch|anschreiben", request.message, re.I) else "en"
            letter = create_cover_letter(
                payload=CoverLetterRequest(
                    job=jobs[0],
                    language=language,
                    tone="professional",
                    profile=profile,
                ),
                fallback_profile=profile,
            )
            actions.append(ChatAction(type="cover_letter", label="Created cover letter draft", data={"cover_letter": model_dump(letter)}))
            navigation = ChatNavigation(view="documents", payload={"cover_letter": model_dump(letter)})
            message = _tool_llm_reply(
                adapter,
                request,
                profile,
                intent="cover_letter",
                tool_summary={
                    "selected_job": {
                        "title": jobs[0].title,
                        "company": jobs[0].company,
                        "location": jobs[0].location,
                    },
                    "letter_preview": letter.text[:1200],
                },
                fallback="I drafted a professional cover letter. Review it before using it in an application.",
            )
            suggestions = ["Make it more concise", "Translate it to German", "Prepare application package"]

    elif intent == "apply":
        jobs = _context_jobs(request)
        if jobs:
            application = create_application(
                payload=ApplicationCreate(
                    job=jobs[0],
                    status="prepared",
                    notes="Prepared by chat assistant.",
                )
            )
            actions.append(
                ChatAction(
                    type="application_prepare",
                    label="Prepared application, confirmation required before submission",
                    status="needs_confirmation",
                    data={"application": model_dump(application)},
                )
            )
            message = "I prepared the application record. Do you want me to submit this application? I will not submit it without your confirmation."
            navigation = ChatNavigation(view="applications")
        else:
            message = "Choose a job first and I can prepare the application. I will always ask before any final submission."
            navigation = ChatNavigation(view="jobs")
        suggestions = ["Show applications", "Create cover letter", "Open job dashboard"]

    elif intent == "tracker":
        applications = [model_dump(item) for item in profile.applications]
        actions.append(ChatAction(type="applications", label=f"Loaded {len(applications)} applications", data={"applications": applications}))
        navigation = ChatNavigation(view="applications")
        message = f"You have {len(applications)} tracked applications. I opened the tracker."

    elif intent == "cv_improve":
        result = improve_cv(CvImproveRequest(cv_text=_attachment_text(request), target_role=" ".join(profile.target_roles[:1])), profile)
        actions.append(ChatAction(type="cv_improve", label="Created an improved CV draft", data={"cv": model_dump(result)}))
        navigation = ChatNavigation(view="documents", payload={"cv_improve": model_dump(result)})
        message = "I created an improved CV draft with stronger keywords and structure. Open Documents to review it."
        suggestions = ["Compare CV versions", "Create a cover letter", "Find jobs for my improved CV"]

    elif intent == "interview":
        role = " ".join(profile.target_roles[:1]) or "target role"
        result = interview_prep(InterviewPrepRequest(role=role), profile)
        actions.append(ChatAction(type="interview_prep", label="Prepared interview questions and answer strategy", data={"interview": model_dump(result)}))
        message = "I prepared technical, behavioral, and regulatory interview questions with an answer strategy."
        suggestions = ["Practice technical questions", "Prepare German interview answers", "Check my chances for a job"]

    elif intent == "roadmap":
        role = " ".join(profile.target_roles[:1]) or "target role"
        result = build_roadmap(RoadmapRequest(target_role=role), profile)
        actions.append(ChatAction(type="skill_roadmap", label="Built skill gap and certification roadmap", data={"roadmap": model_dump(result)}))
        message = "I built a skill gap and certification roadmap based on your target role."
        suggestions = ["Find jobs for this roadmap", "Improve my CV", "Prepare interview"]

    elif intent == "feedback":
        result = analyze_feedback(FeedbackRequest(rejection_text=request.message), profile)
        actions.append(ChatAction(type="rejection_feedback", label="Analyzed rejection feedback", data={"feedback": model_dump(result)}))
        message = "I analyzed the likely rejection reasons and suggested improvements for the next application."
        suggestions = ["Improve my CV", "Create a stronger cover letter", "Find better matching jobs"]

    elif intent == "career_advice":
        advice = _career_advice(profile)
        actions.append(ChatAction(type="career_advice", label="Reviewed your profile and suggested career fields", data=advice))
        message = advice["message"]
        suggestions = advice["suggestions"]
        navigation = ChatNavigation(view="jobs", payload={"querySuggestions": advice["search_queries"]})

    elif intent == "profile":
        actions.append(ChatAction(type="profile", label="Loaded career profile", data={"profile": model_dump(profile)}))
        navigation = ChatNavigation(view="profile")
        message = "I opened your profile. Upload a CV or edit your skills and preferences so I can personalize searches."

    else:
        llm_answer = _general_llm_reply(adapter, request, profile)
        if llm_answer:
            provider, text = llm_answer
            actions.append(
                ChatAction(
                    type="llm_response",
                    label=f"Answered with {provider}",
                    data={"provider": provider},
                )
            )
            message = text
        else:
            message = (
                "I can search jobs, read your CV, rank roles, draft cover letters, and track applications. "
                f"{adapter.manual_mode_note()}"
            )

    return ChatResponse(
        conversation_id=conversation_id,
        message=message,
        actions=actions,
        suggestions=suggestions,
        navigation=navigation,
    )


def _general_llm_reply(adapter: LlmAdapter, request: ChatRequest, profile) -> tuple[str, str] | None:
    profile_context = (
        f"Skills: {', '.join(profile.skills) or 'unknown'}\n"
        f"Languages: {', '.join(profile.languages) or 'unknown'}\n"
        f"Target roles: {', '.join(profile.target_roles) or 'unknown'}\n"
        f"Preferred locations: {', '.join(profile.preferred_locations) or 'unknown'}\n"
        f"CV summary: {(profile.cv_summary or 'unknown')[:3000]}\n"
        f"Attached document text: {_attachment_text(request)[:3000] or 'none'}"
    )
    conversation = _conversation_context(request)
    user = (
        f"Recent conversation:\n{conversation or 'none'}\n\n"
        f"User message:\n{request.message}\n\n"
        f"Profile context:\n{profile_context}"
    )
    try:
        text, provider = adapter.ask_default(GENERAL_SYSTEM, user)
        return provider, text.strip()
    except Exception:
        return None


def _tool_llm_reply(
    adapter: LlmAdapter,
    request: ChatRequest,
    profile,
    intent: str,
    tool_summary: dict[str, object],
    fallback: str,
) -> str:
    if not adapter.available_providers():
        return fallback

    profile_context = {
        "skills": profile.skills,
        "languages": profile.languages,
        "target_roles": profile.target_roles,
        "preferred_locations": profile.preferred_locations,
        "cv_summary": (profile.cv_summary or "")[:2000],
    }
    user = (
        "The platform already ran a tool for the user. Write the assistant's next chat message.\n"
        "Rules:\n"
        "- Be conversational and useful, like a normal LLM chat.\n"
        "- Mention concrete results from the tool summary.\n"
        "- Do not say you can do nothing if the tool succeeded.\n"
        "- Do not repeat the same generic suggestions.\n"
        "- If a cover letter was drafted, say where it is and what to review.\n"
        "- If jobs were searched, explain what search was used and what the user can do next.\n\n"
        f"Recent conversation:\n{_conversation_context(request) or 'none'}\n\n"
        f"User message:\n{request.message}\n\n"
        f"Intent/tool: {intent}\n\n"
        f"Profile:\n{json.dumps(profile_context, default=str)}\n\n"
        f"Tool summary:\n{json.dumps(tool_summary, default=str)}"
    )
    try:
        text, _provider = adapter.ask_default(GENERAL_SYSTEM, user)
        return text.strip() or fallback
    except Exception:
        return fallback


def _career_advice(profile) -> dict[str, object]:
    skills = {item.lower() for item in profile.skills}
    roles = {item.lower() for item in profile.target_roles}
    cv_text = profile.cv_summary.lower()

    fields = []
    if {"ivf", "embryology", "laboratory"} & skills or "embryologist" in roles or "embryology" in cv_text:
        fields.extend(
            [
                "Clinical embryology and IVF laboratory roles",
                "Andrology, fertility diagnostics, and reproductive medicine labs",
                "Biomedical research assistant roles in reproductive biology",
                "Quality control, lab coordination, and regulatory support in fertility clinics",
            ]
        )
    if "research" in skills or "research" in cv_text:
        fields.append("University or hospital research assistant positions")
    if "english" in skills or "deutsch" in skills or profile.languages:
        fields.append("International clinic support or patient-coordination roles where languages help")

    if not fields:
        fields = [
            "Roles connected to your strongest listed skills",
            "Assistant or coordinator roles in your target industry",
            "Entry-to-mid level roles where your CV keywords match the job description",
        ]

    search_queries = [
        "Embryologist",
        "IVF laboratory",
        "Andrology laboratory",
        "Reproductive biology research assistant",
        "Fertility clinic coordinator",
    ]
    if profile.preferred_locations:
        place = profile.preferred_locations[0]
        search_queries = [f"{query} {place}" for query in search_queries]

    message = (
        "Based on your profile, I would focus your job search on these areas:\n\n"
        + "\n".join(f"- {field}" for field in fields[:6])
        + "\n\nYour strongest direction looks like embryology/IVF laboratory work, with research and fertility-clinic support as close alternatives. "
        "For best results, search with specific terms like Embryologist, IVF laboratory, Andrology laboratory, Reproductive biology research assistant, and Fertility clinic coordinator."
    )
    return {
        "message": message,
        "fields": fields[:6],
        "search_queries": search_queries,
        "suggestions": [
            "Find embryologist jobs",
            "Find IVF laboratory jobs",
            "Check my chances for the best job",
        ],
    }
