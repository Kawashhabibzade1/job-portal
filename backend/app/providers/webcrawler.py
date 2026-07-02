import json
import re
from datetime import datetime

from app.models import JobPosting
from app.services.llm_adapter import LlmAdapter


def extract_json_list(text: str) -> list:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    # Try regex matching for the array
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def search_webcrawler(query: str, location: str = "", country: str = "de") -> list[JobPosting]:
    adapter = LlmAdapter()
    if not adapter.available_providers():
        # Fallback if no LLM key is configured
        return []

    system_prompt = (
        "You are a high-precision job crawler and corporate careers website searcher. "
        "Your task is to find and list real, valid corporate career opportunities (vacancies posted on direct company websites) "
        "matching the user's search query, location, and country.\n"
        "Focus on direct company careers pages (e.g., career sections of top local firms, engineering bureaus, tech startups, regional employers) "
        "which often bypass major job aggregator boards.\n\n"
        "Return the results ONLY as a valid JSON list of objects matching this schema:\n"
        "[\n"
        "  {\n"
        "    \"title\": \"Job Title\",\n"
        "    \"company\": \"Company Name\",\n"
        "    \"location\": \"Location (City, Country)\",\n"
        "    \"description\": \"A 2-3 sentence overview of requirements, tech stack, and role.\",\n"
        "    \"source_url\": \"Direct careers/jobs page URL of that specific company\",\n"
        "    \"apply_url\": \"Direct apply/jobs page URL of that specific company\",\n"
        "    \"date_posted\": \"YYYY-MM-DD or null\",\n"
        "    \"is_remote\": true/false\n"
        "  }\n"
        "]\n"
        "Do not include any intro, markdown outside the code block, explanation, or conversational filler. Only return the JSON list."
    )

    user_prompt = (
        f"Find 5 current vacancies directly on company website career portals for:\n"
        f"Query: {query}\n"
        f"Location: {location}\n"
        f"Country: {country}\n"
    )

    try:
        text, _ = adapter.ask_default(system_prompt, user_prompt)
        raw_list = extract_json_list(text)
        
        results = []
        for item in raw_list:
            if not item.get("title") or not item.get("company"):
                continue
            
            # Format date_posted if missing
            posted = item.get("date_posted")
            if not posted:
                posted = datetime.utcnow().strftime("%Y-%m-%d")

            results.append(
                JobPosting(
                    title=item.get("title", ""),
                    company=item.get("company", ""),
                    location=item.get("location") or location or country.upper(),
                    description=item.get("description", ""),
                    source="WebCrawler",
                    source_url=item.get("source_url") or "https://google.com",
                    apply_url=item.get("apply_url") or "https://google.com",
                    date_posted=posted,
                    is_remote=bool(item.get("is_remote", False)),
                    country=country.lower(),
                )
            )
        return results
    except Exception:
        # Graceful failure if LLM fails or keys are not ready
        return []
