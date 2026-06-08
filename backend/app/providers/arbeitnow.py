import requests

from app.models import JobPosting
from app.services.location import location_text_matches


def search_arbeitnow(query: str, location: str = "") -> list[JobPosting]:
    url = "https://www.arbeitnow.com/api/job-board-api"
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json().get("data", [])
    results: list[JobPosting] = []

    query_lower = query.lower().strip()
    for item in data:
        title = item.get("title") or ""
        company = item.get("company_name") or ""
        job_location = item.get("location") or ""
        tags = " ".join(item.get("tags") or [])

        searchable = f"{title} {company} {tags}".lower()
        if query_lower and query_lower not in searchable:
            continue

        if location and not location_text_matches(
            job_location,
            location,
            "remote" in job_location.lower(),
        ):
            continue

        results.append(
            JobPosting(
                title=title,
                company=company,
                location=job_location,
                description=item.get("description"),
                source="Arbeitnow",
                source_url=item.get("url"),
                apply_url=item.get("url"),
                date_posted=str(item.get("created_at")) if item.get("created_at") else None,
                is_remote="remote" in job_location.lower(),
            )
        )

    return results
