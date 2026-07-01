from collections import defaultdict

from app.models import (
    JobPosting,
    SalaryBucket,
    SalaryInsightsRequest,
    SalaryInsightsResponse,
)


COUNTRY_CURRENCY = {
    "de": "EUR", "at": "EUR", "be": "EUR", "ch": "CHF", "gb": "GBP", "tr": "TRY",
}


def salary_insights(payload: SalaryInsightsRequest) -> SalaryInsightsResponse:
    jobs = [j for j in payload.jobs if j.salary_min or j.salary_max]
    if not jobs:
        return SalaryInsightsResponse(note="No salary data found in the provided jobs.")

    buckets_map: dict[str, list[JobPosting]] = defaultdict(list)
    for job in jobs:
        key = (job.title or "Unknown").split(",")[0].split("-")[0].strip()
        buckets_map[key].append(job)

    buckets = []
    all_mins, all_maxs = [], []
    currency = COUNTRY_CURRENCY.get(payload.country, "EUR")

    for role, role_jobs in buckets_map.items():
        mins = [j.salary_min for j in role_jobs if j.salary_min]
        maxs = [j.salary_max for j in role_jobs if j.salary_max]
        all_mins.extend(mins)
        all_maxs.extend(maxs)
        all_vals = mins + maxs
        buckets.append(SalaryBucket(
            role=role,
            country=payload.country,
            min_salary=min(mins) if mins else None,
            max_salary=max(maxs) if maxs else None,
            avg_salary=round(sum(all_vals) / len(all_vals), 2) if all_vals else None,
            currency=currency,
            sample_count=len(role_jobs),
        ))

    all_vals = all_mins + all_maxs
    return SalaryInsightsResponse(
        buckets=sorted(buckets, key=lambda b: b.sample_count, reverse=True),
        overall_min=min(all_mins) if all_mins else None,
        overall_max=max(all_maxs) if all_maxs else None,
        overall_avg=round(sum(all_vals) / len(all_vals), 2) if all_vals else None,
        sample_count=len(jobs),
        note=f"Based on {len(jobs)} jobs with salary data.",
    )
