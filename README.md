# Job Portal MVP

A lightweight job-search portal with a FastAPI backend and a React/Vite frontend.

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API runs on `http://127.0.0.1:8000`.

Available endpoints:

- `GET /health`
- `GET /api/jobs/search?query=python&location=berlin&country=de`
- `GET /api/jobs/scrape?query=python&location=berlin&sources=indeed,linkedin`
- `GET /api/jobs/cache`
- `DELETE /api/jobs/cache`
- `POST /api/jobs/deduplicate`

Adzuna, JSearch, and Jooble require API keys. The country source picker only shows local or country-specific portals; generic aggregators are not shown as local country sources.

Configured providers:

- Arbeitsagentur: German job listings with apply links
- Arbeitnow: Europe-focused tech jobs
- Indeed: German search-result scraping with retry and 1-hour in-memory cache
- LinkedIn: public jobs-page scraping with retry and 1-hour in-memory cache
- Karriere.at: Austria-focused public portal search
- Jobs.ch: Switzerland-focused public portal search
- Jobup.ch: Switzerland-focused public portal search
- Reed UK: United Kingdom-focused public portal search
- NHS Jobs: United Kingdom health-sector public portal search
- HealthJobsUK: United Kingdom health-sector portal search
- Jobs.ac.uk: United Kingdom academic job search
- New Scientist Jobs: United Kingdom science job portal
- IFS: United Kingdom Institute for Fiscal Studies jobs page
- ARCS Community: United Kingdom ARCS jobs board
- NorthCyprus.cv: Northern Cyprus local jobs and university-focused discovery
- İş Kıbrıs: Northern Cyprus local jobs portal
- TRNC Research Portals: EMU, NEU, and CIU academic/research application pages
- Adzuna: broad job search with `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`
- JSearch: RapidAPI job search with `JSEARCH_API_KEY`
- Jooble: broad job search with `JOOBLE_API_KEY`
- Remotive: remote jobs

Local source map:

- Germany: `arbeitsagentur`, `arbeitnow`, `indeed`, `linkedin`
- Austria: `karriere_at`
- Switzerland: `jobs_ch`, `jobup_ch`
- United Kingdom: `reed_uk`, `nhs_jobs`, `healthjobs_uk`, `jobs_ac_uk`, `new_scientist_jobs`, `ifs_uk`, `arcs_community`
- Northern Cyprus: `northcyprus_cv`, `iskibris`, `trnc_research`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://127.0.0.1:5173`.

## Scraping configuration

The scraper is designed for short serverless requests and keeps results in memory for one hour:

```bash
SCRAPER_TIMEOUT=30000
SCRAPER_MAX_RETRIES=3
CACHE_DURATION=3600000
VERCEL_DEPLOYMENT=true
```

Use `refresh=true` to bypass cache. Scraping endpoints are rate-limited to 5 requests per IP per minute. Public job pages can block automated traffic; when that happens, the API returns per-source errors and uses cached data when available. Check each provider's robots.txt and terms before production use, especially LinkedIn.
