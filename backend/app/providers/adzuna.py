import requests

from app.config import settings
from app.models import JobPosting


def search_adzuna(query: str, location: str = "", country: str = "de") -> list[JobPosting]:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        return []

    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "what": query,
        "where": location,
        "results_per_page": 20,
        "content-type": "application/json",
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    data = response.json().get("results", [])
    results: list[JobPosting] = []

    for item in data:
        company = item.get("company", {}).get("display_name")

        results.append(
            JobPosting(
                title=item.get("title", ""),
                company=company,
                location=item.get("location", {}).get("display_name"),
                description=item.get("description"),
                source="Adzuna",
                source_url=item.get("redirect_url"),
                apply_url=item.get("redirect_url"),
                date_posted=item.get("created"),
                salary_min=item.get("salary_min"),
                salary_max=item.get("salary_max"),
                currency=None,
                is_remote=None,
            )
        )

    return results

