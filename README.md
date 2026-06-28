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

Adzuna, JSearch, and Jooble require API keys. The country source picker only shows local or country-specific portals; generic aggregators are not shown as local country sources.

Configured providers:

- Arbeitsagentur: German job listings with apply links
- Arbeitnow: Europe-focused tech jobs
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
- Adzuna: broad job search with `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`
- JSearch: RapidAPI job search with `JSEARCH_API_KEY`
- Jooble: broad job search with `JOOBLE_API_KEY`
- Remotive: remote jobs

Local source map:

- Germany: `arbeitsagentur`, `arbeitnow`
- Austria: `karriere_at`
- Switzerland: `jobs_ch`, `jobup_ch`
- United Kingdom: `reed_uk`, `nhs_jobs`, `healthjobs_uk`, `jobs_ac_uk`, `new_scientist_jobs`, `ifs_uk`, `arcs_community`
- Northern Cyprus: no local source configured yet

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://127.0.0.1:5173`.
