import requests

from app.config import settings
from app.models import JobPosting


def search_jsearch(query: str, location: str = "") -> list[JobPosting]:
    if not settings.jsearch_api_key:
        return []

    search_query = " ".join(part for part in [query.strip(), location.strip()] if part)
    if not search_query:
        search_query = "jobs"

    response = requests.get(
        "https://jsearch.p.rapidapi.com/search",
        headers={
            "X-RapidAPI-Key": settings.jsearch_api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        },
        params={
            "query": search_query,
            "page": "1",
            "num_pages": "1",
        },
        timeout=20,
    )
    response.raise_for_status()

    results: list[JobPosting] = []
    for item in response.json().get("data", []):
        location_parts = [
            item.get("job_city"),
            item.get("job_state"),
            item.get("job_country"),
        ]
        job_location = ", ".join(part for part in location_parts if part)

        results.append(
            JobPosting(
                title=item.get("job_title", ""),
                company=item.get("employer_name"),
                location=job_location or None,
                description=item.get("job_description"),
                source="JSearch",
                source_url=item.get("job_google_link"),
                apply_url=item.get("job_apply_link"),
                date_posted=item.get("job_posted_at_datetime_utc"),
                salary_min=item.get("job_min_salary"),
                salary_max=item.get("job_max_salary"),
                currency=item.get("job_salary_currency"),
                is_remote=item.get("job_is_remote"),
            )
        )

    return results

