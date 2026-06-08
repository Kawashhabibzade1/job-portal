import requests

from app.models import JobPosting
from app.services.location import location_text_matches


def search_remotive(query: str, location: str = "") -> list[JobPosting]:
    params = {"limit": 25}
    if query.strip():
        params["search"] = query.strip()

    response = requests.get(
        "https://remotive.com/api/remote-jobs",
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    results: list[JobPosting] = []

    for item in response.json().get("jobs", []):
        candidate_location = item.get("candidate_required_location") or "Remote"
        if location and not location_text_matches(candidate_location, location, True):
            continue

        results.append(
            JobPosting(
                title=item.get("title", ""),
                company=item.get("company_name"),
                location=candidate_location,
                description=item.get("description"),
                source="Remotive",
                source_url=item.get("url"),
                apply_url=item.get("url"),
                date_posted=item.get("publication_date"),
                is_remote=True,
            )
        )

    return results
