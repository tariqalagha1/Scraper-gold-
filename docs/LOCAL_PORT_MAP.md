# Local Port Map (Multi-Project Safe)

When you run several projects at the same time, use this port map for `scraper-main` to avoid collisions.

## Recommended ports for this project

- Frontend (React): `43102`
- Backend API (FastAPI): `8001`
- Redis: `46379`
- PostgreSQL: `45432`

## Quick start commands

### Single-command startup

```bash
./scripts/dev-up.sh
```

### Frontend (manual)

```bash
cd frontend
PORT=43102 REACT_APP_API_URL=http://127.0.0.1:8001/api/v1 npm start
```

### Backend API (manual)

```bash
cd backend
source venv/bin/activate
PORT=8001 uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

## Environment alignment

If you use a local `.env`, align these values:

```dotenv
REACT_APP_API_URL=http://127.0.0.1:8001/api/v1
REACT_APP_API_KEY=dev-api-key-change-me
REACT_APP_API_KEY_HEADER_NAME=X-API-Key
BACKEND_PORT=8001
FRONTEND_PORT=43102
REDIS_PORT=46379
POSTGRES_PORT=45432
DATABASE_URL=postgresql+asyncpg://scraper:scraper_password_change_me@127.0.0.1:45432/scraper_db
REDIS_URL=redis://127.0.0.1:46379/0
API_KEY=dev-api-key-change-me
API_KEY_HEADER_NAME=X-API-Key
```

## Check collisions before starting

```bash
bash scripts/check-local-ports.sh
```
