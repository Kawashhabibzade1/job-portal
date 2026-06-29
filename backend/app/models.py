from typing import Optional

from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    source: str
    sources: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    apply_url: Optional[str] = None
    date_posted: Optional[str] = None
    scraped_at: Optional[str] = None
    salary_text: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    is_remote: Optional[bool] = None


class JobSearchResponse(BaseModel):
    query: str = ""
    location: str = ""
    country: str = "de"
    count: int
    jobs: list[JobPosting]
    sources: dict[str, int] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
