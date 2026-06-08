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

Adzuna, JSearch, and Jooble require API keys. Arbeitnow, Remotive, and Arbeitsagentur can return results without personal keys.

Configured providers:

- Arbeitsagentur: German job listings with apply links
- Arbeitnow: Europe-focused tech jobs
- Remotive: remote jobs
- Adzuna: broad job search with `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`
- JSearch: RapidAPI job search with `JSEARCH_API_KEY`
- Jooble: broad job search with `JOOBLE_API_KEY`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://127.0.0.1:5173`.
