import requests

from app.config import settings
from app.models import JobPosting


def search_jooble(query: str, location: str = "") -> list[JobPosting]:
    if not settings.jooble_api_key:
        return []

    response = requests.post(
        f"https://jooble.org/api/{settings.jooble_api_key}",
        json={
            "keywords": query,
            "location": location,
            "radius": "80",
            "page": "1",
            "ResultOnPage": "25",
            "companysearch": "false",
        },
        timeout=20,
    )
    response.raise_for_status()

    results: list[JobPosting] = []
    for item in response.json().get("jobs", []):
        results.append(
            JobPosting(
                title=item.get("title") or "",
                company=item.get("company"),
                location=item.get("location"),
                description=item.get("snippet"),
                source="Jooble",
                source_url=item.get("link"),
                apply_url=item.get("link"),
                date_posted=item.get("updated"),
                is_remote=None,
            )
        )

    return results
