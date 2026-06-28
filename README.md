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

Adzuna, JSearch, and Jooble require API keys. Arbeitnow, Remotive, Arbeitsagentur, and the direct portal searches can return results without personal keys.

Configured providers:

- Arbeitsagentur: German job listings with apply links
- Arbeitnow: Europe-focused tech jobs
- Remotive: remote jobs
- Adzuna: broad job search with `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`
- JSearch: RapidAPI job search with `JSEARCH_API_KEY`
- Jooble: broad job search with `JOOBLE_API_KEY`
- Karriere.at: Austria-focused public portal search
- Jobs.ch: Switzerland-focused public portal search
- Jobup.ch: Switzerland-focused public portal search
- Reed UK: United Kingdom-focused public portal search

Country coverage notes:

- Austria: use `country=at` with Adzuna/JSearch/Jooble and enable `karriere_at` for a well-known local Austrian portal.
- Switzerland: use `country=ch` with Adzuna/JSearch/Jooble and enable `jobs_ch` or `jobup_ch` for well-known local Swiss portals.
- United Kingdom: use `country=gb` with Adzuna/JSearch/Jooble and enable `reed_uk` for a broad local UK portal.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://127.0.0.1:5173`.
