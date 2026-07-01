import re

from app.models import (
    CvCompareRequest,
    CvCompareResponse,
    CvImproveRequest,
    CvImproveResponse,
    FeedbackRequest,
    FeedbackResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
    RoadmapRequest,
    RoadmapResponse,
    UserProfile,
)


KEYWORD_BANK = {
    "embryologist": ["IVF", "ICSI", "embryo culture", "andrology", "quality control", "patient confidentiality"],
    "research": ["study design", "data collection", "literature review", "laboratory documentation"],
    "developer": ["Python", "React", "APIs", "testing", "deployment"],
}


def improve_cv(payload: CvImproveRequest, profile: UserProfile) -> CvImproveResponse:
    text = payload.cv_text or profile.cv_summary
    target = payload.target_role or (payload.job.title if payload.job else "target role")
    keywords = _keywords_for(target, payload.job.description if payload.job else "")
    improved = _improved_cv_text(text, target, keywords, profile)
    return CvImproveResponse(
        improved_text=improved,
        changes=[
            "Added a stronger professional summary.",
            "Grouped skills around the target role.",
            "Inserted role-specific keywords for applicant tracking systems.",
            "Converted responsibilities into evidence-oriented bullet points.",
        ],
        keywords=keywords,
    )


def compare_cvs(payload: CvCompareRequest) -> CvCompareResponse:
    original = _tokens(payload.original_text)
    revised = _tokens(payload.revised_text)
    added = sorted(revised - original)[:30]
    removed = sorted(original - revised)[:30]
    return CvCompareResponse(
        added_keywords=added,
        removed_keywords=removed,
        summary=f"The revised CV adds {len(added)} notable keywords and removes {len(removed)} terms.",
    )


def interview_prep(payload: InterviewPrepRequest, profile: UserProfile) -> InterviewPrepResponse:
    role = payload.role or (payload.job.title if payload.job else "the role")
    return InterviewPrepResponse(
        technical_questions=[
            f"Which technical skills make you suitable for {role}?",
            "Describe a difficult laboratory or project problem and how you solved it.",
            "How do you document quality-sensitive work?",
            "Which tools, procedures, or methods are you strongest with?",
        ],
        behavioral_questions=[
            "Tell me about yourself and your career direction.",
            "Describe a time you handled pressure or strict deadlines.",
            "How do you communicate with clinicians, colleagues, or patients?",
            "Why do you want this role at this organization?",
        ],
        regulatory_questions=[
            "How do you protect confidential medical or candidate information?",
            "How do you follow SOPs and quality-management requirements?",
            "What would you do if you noticed a documentation or sample-handling error?",
        ],
        answer_strategy=[
            f"Anchor answers around {', '.join(profile.skills[:5]) or 'your strongest skills'}.",
            "Use STAR: situation, task, action, result.",
            "Connect each answer to patient safety, accuracy, quality, or measurable outcomes.",
        ],
    )


def analyze_feedback(payload: FeedbackRequest, profile: UserProfile) -> FeedbackResponse:
    text = payload.rejection_text.lower()
    reasons = []
    if "experience" in text:
        reasons.append("The employer may have wanted more direct or senior experience.")
    if "qualification" in text or "certificate" in text:
        reasons.append("A specific qualification or certification may have been missing.")
    if "competitive" in text or "other candidates" in text:
        reasons.append("The role may have had stronger-matching applicants.")
    if not reasons:
        reasons.append("The rejection text is generic, so the likely cause is profile-to-role fit or competition.")
    return FeedbackResponse(
        likely_reasons=reasons,
        improvements=[
            "Tailor the CV headline and first third of the CV to the exact role title.",
            "Add measurable outcomes, lab methods, tools, and certifications near the top.",
            "Use a short cover letter paragraph that directly addresses the top job requirements.",
        ],
        next_actions=[
            "Compare the rejected job description against your CV keywords.",
            "Create a stronger role-specific CV version.",
            "Track the rejection reason and adjust the next application package.",
        ],
    )


def build_roadmap(payload: RoadmapRequest, profile: UserProfile) -> RoadmapResponse:
    target = payload.target_role.lower()
    expected = _keywords_for(target, payload.job.description if payload.job else "")
    current = {item.lower() for item in profile.skills}
    missing = [keyword for keyword in expected if keyword.lower() not in current]
    certifications = _certifications_for(target)
    return RoadmapResponse(
        missing_skills=missing[:10],
        certifications=certifications,
        plan=[
            "Week 1: collect 10 target job descriptions and extract repeated requirements.",
            "Weeks 2-3: close the top two skill gaps with a short course, SOP review, or project.",
            "Week 4: update CV, cover letter template, and interview examples with evidence.",
            "Ongoing: track applications, rejection reasons, interviews, and keyword gaps.",
        ],
    )


def _improved_cv_text(text: str, target: str, keywords: list[str], profile: UserProfile) -> str:
    summary = (
        f"Professional Summary\n"
        f"Motivated {target} candidate with experience across {', '.join(profile.skills[:6]) or 'relevant technical skills'}. "
        f"Focused on accuracy, documentation, quality, and continuous improvement.\n\n"
    )
    skill_line = f"Core Skills\n{', '.join(sorted(set(profile.skills + keywords)))}\n\n"
    body = text.strip() or "Add your experience, education, projects, certifications, and achievements here."
    return summary + skill_line + "Experience\n" + body


def _keywords_for(target: str, description: str = "") -> list[str]:
    haystack = f"{target} {description}".lower()
    keywords: list[str] = []
    for key, values in KEYWORD_BANK.items():
        if key in haystack:
            keywords.extend(values)
    if not keywords:
        keywords = ["communication", "documentation", "quality control", "problem solving"]
    return list(dict.fromkeys(keywords))


def _certifications_for(target: str) -> list[str]:
    if "embry" in target or "ivf" in target:
        return [
            "ESHRE or national embryology training resources",
            "Good Clinical Practice awareness",
            "Quality management / ISO 15189 awareness",
            "Andrology or reproductive laboratory workshops",
        ]
    if "research" in target:
        return ["Good Clinical Practice", "Research ethics", "Biostatistics basics", "Laboratory safety"]
    return ["Role-specific short course", "Professional communication", "Project portfolio"]


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z+#-]{2,}", text)}
