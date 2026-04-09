# Smart Scraper

AI-powered multi-agent web scraping platform with a React frontend, FastAPI backend, Celery workers, and export-ready results.

## What It Does

- Creates scraping jobs with configurable targets and extraction behavior
- Runs an agentic scraping pipeline with orchestration and processing stages
- Supports authenticated SaaS-style workflows and API key access
- Generates structured results and markdown snapshots
- Exports results in multiple formats

## Stack

- Frontend: React, React Router, MUI, Tailwind
- Backend: FastAPI, SQLAlchemy, Alembic
- Queue: Celery, Redis
- Scraping: Playwright, BeautifulSoup, lxml
- AI/Orchestration: OpenAI, LangChain, LangGraph, CrewAI
- Storage/Vector: FAISS, file-based storage

## Project Structure

```text
frontend/   React application
backend/    FastAPI app, workers, models, migrations, tests
design/     UI concepts and design references
docs/       Local docs and environment notes
scripts/    Utility and test scripts
```

## Local Development

### Frontend

```bash
cd frontend
npm install
npm start
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Worker

```bash
cd backend
source venv/bin/activate
celery -A app.queue.celery_app worker --loglevel=info
```

## Environment

Typical local and production values include:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `CORS_ORIGINS`
- `PLAYWRIGHT_HEADLESS`
- `REACT_APP_API_URL`

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment details.

## Deployment

Recommended deployment shape:

- Frontend on Vercel
- Backend API on Railway
- Worker on Railway
- PostgreSQL on Neon, Supabase, or Railway
- Redis on Upstash or Redis Cloud

Release and infrastructure notes are documented in:

- [DEPLOYMENT.md](/Users/tariqalagha/Desktop/scraper-main/DEPLOYMENT.md)
- [FOLDER-STRUCTURE.md](FOLDER-STRUCTURE.md)
- [docs/LOCAL_PORT_MAP.md](docs/LOCAL_PORT_MAP.md)

## Testing

Backend and frontend both include tests.

Examples:

```bash
cd backend
pytest
```

```bash
cd frontend
npm test
```

## Suggested GitHub Description

`AI-powered multi-agent web scraping platform with FastAPI, React, Celery, Playwright, and export-ready intelligence workflows.`
