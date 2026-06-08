import requests

from app.models import JobPosting


BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
DETAIL_BASE_URL = "https://www.arbeitsagentur.de/jobsuche/jobdetail"


def _location(item: dict) -> str | None:
    place = item.get("arbeitsort") or {}
    parts = [
        place.get("ort"),
        place.get("region"),
        place.get("land"),
    ]
    return ", ".join(dict.fromkeys(part for part in parts if part)) or None


def _apply_url(item: dict) -> str | None:
    if item.get("externeUrl"):
        return item["externeUrl"]
    if item.get("refnr"):
        return f"{DETAIL_BASE_URL}/{item['refnr']}"
    return None


def search_arbeitsagentur(query: str, location: str = "") -> list[JobPosting]:
    params = {
        "was": query,
        "wo": location,
        "size": 25,
        "page": 1,
        "angebotsart": 1,
        "pav": "false",
    }
    response = requests.get(
        BASE_URL,
        headers={"X-API-Key": "jobboerse-jobsuche"},
        params={key: value for key, value in params.items() if value not in {"", None}},
        timeout=20,
    )
    response.raise_for_status()

    results: list[JobPosting] = []
    for item in response.json().get("stellenangebote", []):
        apply_url = _apply_url(item)
        results.append(
            JobPosting(
                title=item.get("titel") or item.get("beruf") or "",
                company=item.get("arbeitgeber"),
                location=_location(item),
                description=item.get("beruf"),
                source="Arbeitsagentur",
                source_url=apply_url,
                apply_url=apply_url,
                date_posted=item.get("aktuelleVeroeffentlichungsdatum"),
                is_remote=None,
            )
        )

    return results

