import requests

from app.models import JobPosting


def link_is_live(url: str, timeout: int = 8) -> bool:
    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        if response.status_code == 405:
            response = requests.get(url, allow_redirects=True, timeout=timeout)
        return response.status_code < 400
    except requests.RequestException:
        return False


def verify_job_links(jobs: list[JobPosting], limit: int = 20) -> dict[str, bool]:
    statuses: dict[str, bool] = {}
    for job in jobs[:limit]:
        url = job.apply_url or job.source_url
        if url:
            statuses[url] = link_is_live(url)
    return statuses

