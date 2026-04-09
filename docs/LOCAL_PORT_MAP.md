# Local Port Map (Multi-Project Safe)

When you run several projects at the same time, use this port map for `scraper-main` to avoid collisions.

## Recommended ports for this project

- Frontend (React): `43101`
- Backend API (FastAPI): `43102`
- Redis: `46379`
- PostgreSQL: `45432`

## Quick start commands

### Frontend

```bash
cd frontend
npm run start:43101:api43102
```

### Backend API

```bash
cd backend
source venv/bin/activate
PORT=43102 uvicorn app.main:app --host 127.0.0.1 --port 43102 --reload
```

### Celery worker (if needed)

```bash
cd backend
source venv/bin/activate
REDIS_URL=redis://127.0.0.1:46379/0 celery -A app.core.celery:celery_app worker -l info
```

## Environment alignment

If you use a local `.env`, align these values:

```dotenv
REACT_APP_API_URL=http://127.0.0.1:43102/api/v1
BACKEND_PORT=43102
FRONTEND_PORT=43101
REDIS_PORT=46379
POSTGRES_PORT=45432
DATABASE_URL=postgresql+asyncpg://scraper:scraper_password_change_me@127.0.0.1:45432/scraper_db
REDIS_URL=redis://127.0.0.1:46379/0
```

## Check collisions before starting

```bash
bash scripts/check-local-ports.sh
```
