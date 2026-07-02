import re

from app.models import (
    CvCompareRequest,
    CvCompareResponse,
    CvImproveRequest,
    CvImproveResponse,
    CvSuggestion,
    CvSuggestionsResponse,
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


def analyze_cv_suggestions(payload: CvImproveRequest, profile: UserProfile) -> CvSuggestionsResponse:
    """Return structured, actionable CV improvement suggestions as cards."""
    text = payload.cv_text or profile.cv_summary
    target = payload.target_role or (payload.job.title if payload.job else "target role")
    keywords = _keywords_for(target, payload.job.description if payload.job else "")
    suggestions: list[CvSuggestion] = []

    # Professional Summary check
    if not text or len(text) < 100:
        suggestions.append(CvSuggestion(
            section="Professional Summary",
            issue="Your CV summary is missing or very short.",
            recommendation="Write a 3–5 sentence professional summary highlighting your top skills, years of experience, and career goal for the target role.",
            priority="high",
        ))
    elif "summary" not in text.lower() and "profile" not in text.lower():
        suggestions.append(CvSuggestion(
            section="Professional Summary",
            issue="No clear professional summary section detected.",
            recommendation="Add a dedicated 'Professional Summary' or 'Profile' section at the top that is tailored to the role.",
            priority="high",
        ))

    # Keywords check
    text_lower = text.lower()
    missing_keywords = [kw for kw in keywords if kw.lower() not in text_lower]
    if missing_keywords:
        suggestions.append(CvSuggestion(
            section="Keywords & ATS",
            issue=f"Missing {len(missing_keywords)} role-specific keywords: {', '.join(missing_keywords[:5])}.",
            recommendation=f"Add these keywords naturally in your skills or experience section: {', '.join(missing_keywords[:8])}.",
            priority="high",
        ))

    # Quantified achievements
    if not any(char.isdigit() for char in text):
        suggestions.append(CvSuggestion(
            section="Achievements",
            issue="No measurable achievements detected (no numbers or percentages).",
            recommendation="Add quantified results e.g. 'Increased lab throughput by 30%', 'Managed 5-person team', 'Processed 200+ samples/week'.",
            priority="high",
        ))

    # Skills section
    skills_in_text = [s.lower() for s in profile.skills if s.lower() in text_lower]
    if len(skills_in_text) < 3:
        suggestions.append(CvSuggestion(
            section="Skills",
            issue="Your profile skills are not well-reflected in the CV text.",
            recommendation=f"Explicitly list your skills: {', '.join(profile.skills[:8]) or 'add your key competencies'}.",
            priority="medium",
        ))

    # Languages
    if not profile.languages:
        suggestions.append(CvSuggestion(
            section="Languages",
            issue="No languages listed in your profile.",
            recommendation="Add a 'Languages' section with your proficiency level (e.g. English – C1, German – B2).",
            priority="medium",
        ))

    # Action verbs
    weak_verbs = ["responsible for", "helped with", "worked on", "involved in"]
    if any(v in text_lower for v in weak_verbs):
        suggestions.append(CvSuggestion(
            section="Experience Bullets",
            issue="Weak passive language detected ('responsible for', 'helped with', etc.).",
            recommendation="Replace passive phrases with strong action verbs: 'Led', 'Developed', 'Optimized', 'Reduced', 'Achieved', 'Managed'.",
            priority="medium",
        ))

    # Education / Certifications
    if "education" not in text_lower and "degree" not in text_lower and "university" not in text_lower:
        suggestions.append(CvSuggestion(
            section="Education",
            issue="No education section detected.",
            recommendation="Add your highest qualification, institution, year, and any relevant modules or thesis topics.",
            priority="medium",
        ))

    # Contact info
    if "@" not in text and "linkedin" not in text_lower:
        suggestions.append(CvSuggestion(
            section="Contact Information",
            issue="Email or LinkedIn profile not visible in the CV.",
            recommendation="Ensure your email, LinkedIn URL, and optionally GitHub or portfolio link appear at the top.",
            priority="low",
        ))

    # Calculate overall score
    total_possible = 8
    issues_count = len(suggestions)
    score = max(0, min(100, int(((total_possible - issues_count) / total_possible) * 100)))

    if score >= 80:
        summary = "Your CV is in great shape! A few minor tweaks will make it perfect."
    elif score >= 60:
        summary = "Your CV has a solid foundation. Address the high-priority suggestions to significantly improve your chances."
    else:
        summary = "Your CV needs important improvements. Focus on the high-priority items first — they will have the biggest impact."

    return CvSuggestionsResponse(suggestions=suggestions, overall_score=score, summary=summary)



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
