# Smart Scraper SaaS Deployment

## Architecture

- Frontend: Vercel
- Backend API: Railway
- Worker: Railway
- PostgreSQL: Neon, Supabase, or Railway Postgres
- Redis: Upstash Redis or Redis Cloud
- Monitoring: Better Stack Uptime

## 1. Production Env

Create local template:

```bash
cp .env.production.example .env.production
```

Generate a secret:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
```

Do not commit real secrets. Put them into Railway and Vercel environment variables.

Required backend variables:

```env
ENVIRONMENT=production
DEBUG=false
RELOAD=false
SECRET_KEY=replace-me
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME
REDIS_URL=redis://default:PASSWORD@HOST:6379
CORS_ORIGINS=https://app.example.com
PLAYWRIGHT_HEADLESS=true
```

Required frontend variable:

```env
REACT_APP_API_URL=https://api.example.com/api/v1
```

## 2. Database

Use Neon, Supabase, or Railway PostgreSQL. If provider gives a sync URL like:

```env
postgres://USER:PASSWORD@HOST:5432/DBNAME
```

convert it for SQLAlchemy async:

```env
postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME
```

For Supabase specifically:

1. Use the Postgres connection string from Supabase (prefer pooler for production).
2. Convert the scheme to async SQLAlchemy:

```env
postgresql+asyncpg://USER:PASSWORD@HOST:6543/postgres?ssl=require
```

3. Set that as `DATABASE_URL` for both API and worker services.

Validate cloud DB connectivity before deploy:

```bash
cd backend
venv/bin/python scripts/check_cloud_db.py
```

## 3. Redis

Create an Upstash Redis database or Redis Cloud instance and copy the Redis URL into:

```env
REDIS_URL=redis://default:PASSWORD@HOST:6379
```

## 4. Backend API on Railway

Create a Railway project and add a service from this repo root.

Build source:

```text
Dockerfile
```

Start command:

```bash
./backend/scripts/start_api.sh
```

Set Railway variables:

```env
ENVIRONMENT=production
DEBUG=false
RELOAD=false
SECRET_KEY=...
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
CORS_ORIGINS=https://app.example.com
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT=30000
REQUEST_TIMEOUT_SECONDS=60
JOB_CREATE_RATE_LIMIT=20
RUN_CREATE_RATE_LIMIT=20
```

Run migrations before first traffic:

```bash
./backend/scripts/release.sh
```

If using Railway CLI:

```bash
railway login
railway link
railway run ./backend/scripts/release.sh
```

## 5. Worker on Railway

Create a second Railway service from the same repo and same Dockerfile.

Start command:

```bash
./backend/scripts/start_worker.sh
```

Set the same backend environment variables on the worker service.

Optional worker tuning:

```env
CELERY_CONCURRENCY=4
CELERY_TASK_TIME_LIMIT=300
CELERY_TASK_SOFT_TIME_LIMIT=270
```

## 6. Frontend on Vercel

Project settings:

- Root Directory: `frontend`
- Framework preset: Create React App
- Build Command: `npm run build`
- Output Directory: `build`

Environment variable:

```env
REACT_APP_API_URL=https://api.example.com/api/v1
```

Vercel CLI deploy:

```bash
cd frontend
npm install
vercel
vercel --prod
```

## 7. Domains and HTTPS

Backend on Railway:

1. Open the backend Railway service.
2. Go to Settings -> Networking.
3. Add custom domain `api.example.com`.
4. Add the provided CNAME in your DNS provider.
5. Wait for Railway SSL issuance.

Frontend on Vercel:

1. Open the Vercel project.
2. Go to Settings -> Domains.
3. Add `app.example.com`.
4. Add required DNS records.
5. Vercel will issue SSL automatically.

## 8. Monitoring

Recommended checks:

- `https://api.example.com/health`
- `https://api.example.com/health/full`
- `https://app.example.com`

Better Stack setup:

1. Create 3 uptime monitors for the URLs above.
2. Interval: 1 minute.
3. Alert channel: email + Slack.
4. Expected backend response: `200`.

Useful Railway logs:

```bash
railway logs
```

Useful Vercel logs:

```bash
vercel logs app.example.com
```

## 9. First Production Rollout

1. Provision Postgres.
2. Provision Redis.
3. Set backend env vars on Railway API service.
4. Set same env vars on Railway worker service.
5. Run migrations:

```bash
railway run ./backend/scripts/release.sh
```

6. Deploy Railway API.
7. Deploy Railway worker.
8. Set `REACT_APP_API_URL` on Vercel.
9. Deploy frontend:

```bash
cd frontend
vercel --prod
```

10. Attach `api.example.com` to Railway.
11. Attach `app.example.com` to Vercel.
12. Add uptime monitors.

## 10. Smoke Test Commands

Health:

```bash
curl https://api.example.com/health
curl https://api.example.com/health/full
```

Login:

```bash
curl -X POST https://api.example.com/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=YOUR_EMAIL&password=YOUR_PASSWORD"
```

Authenticated jobs:

```bash
curl https://api.example.com/api/v1/jobs \
  -H "Authorization: Bearer YOUR_JWT"
```

API key auth:

```bash
curl https://api.example.com/api/v1/account/summary \
  -H "X-API-Key: YOUR_USER_API_KEY"
```
