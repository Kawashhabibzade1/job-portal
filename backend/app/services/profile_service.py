from datetime import datetime, timezone
from uuid import uuid4

from app.models import (
    ApplicationCreate,
    ApplicationRecord,
    ApplicationUpdate,
    ProfileUpdate,
    UploadedDocument,
    UserProfile,
)
from app.services.storage import JsonStore
from app.services.serialization import model_dump


PROFILE_STORE = JsonStore("profile.json", model_dump(UserProfile()))

COMMON_SKILLS = [
    "python",
    "javascript",
    "typescript",
    "react",
    "fastapi",
    "django",
    "sql",
    "postgres",
    "excel",
    "project management",
    "data analysis",
    "machine learning",
    "laboratory",
    "ivf",
    "embryology",
    "research",
    "regulatory",
    "german",
    "english",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_profile() -> UserProfile:
    return UserProfile(**PROFILE_STORE.read())


def save_profile(profile: UserProfile) -> UserProfile:
    PROFILE_STORE.write(model_dump(profile))
    return profile


def update_profile(update: ProfileUpdate) -> UserProfile:
    profile = get_profile()
    data = model_dump(profile)
    for key, value in model_dump(update, exclude_unset=True).items():
        if value is not None:
            data[key] = value
    return save_profile(UserProfile(**data))


def merge_unique(current: list[str], additions: list[str]) -> list[str]:
    seen = {item.lower(): item for item in current}
    for item in additions:
        cleaned = item.strip()
        if cleaned and cleaned.lower() not in seen:
            seen[cleaned.lower()] = cleaned
    return list(seen.values())


def infer_profile_from_document(document: UploadedDocument) -> UserProfile:
    profile = get_profile()
    text = document.text.lower()
    skills = [skill for skill in COMMON_SKILLS if skill in text]
    languages = [language.title() for language in ["english", "german", "turkish"] if language in text]
    roles = []
    for role in ["developer", "engineer", "data scientist", "embryologist", "research assistant"]:
        if role in text:
            roles.append(role.title())

    profile.skills = merge_unique(profile.skills, [skill.title() for skill in skills])
    profile.languages = merge_unique(profile.languages, languages)
    profile.target_roles = merge_unique(profile.target_roles, roles)
    if document.document_type == "cv":
        profile.cv_summary = document.text[:1200]
    profile.documents = merge_unique(profile.documents, [document.id])
    return save_profile(profile)


def list_applications() -> list[ApplicationRecord]:
    return get_profile().applications


def create_application(payload: ApplicationCreate) -> ApplicationRecord:
    timestamp = now_iso()
    application = ApplicationRecord(
        id=str(uuid4()),
        job=payload.job,
        status=payload.status,
        notes=payload.notes,
        cover_letter_id=payload.cover_letter_id,
        created_at=timestamp,
        updated_at=timestamp,
    )
    profile = get_profile()
    profile.applications.insert(0, application)
    save_profile(profile)
    return application


def update_application(application_id: str, payload: ApplicationUpdate) -> ApplicationRecord | None:
    profile = get_profile()
    for index, application in enumerate(profile.applications):
        if application.id != application_id:
            continue
        data = model_dump(application)
        for key, value in model_dump(payload, exclude_unset=True).items():
            if value is not None:
                data[key] = value
        data["updated_at"] = now_iso()
        updated = ApplicationRecord(**data)
        profile.applications[index] = updated
        save_profile(profile)
        return updated
    return None
