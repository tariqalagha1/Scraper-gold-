# Smart Scraper - Online Deployment Guide

## Quick Deploy (Vercel + Railway)

Your app is ready to deploy! Follow these steps to get live in 15 minutes.

---

## 📋 Prerequisites

- GitHub account with repo connected: https://github.com/tariqalagha1/Scraper-gold-
- Vercel account: https://vercel.com (free)
- Railway account: https://railway.app (free with $5 credit)

---

## 🚀 Step 1: Deploy Frontend to Vercel

### 1.1 Import Repository

1. Go to **https://vercel.com/new**
2. Click **"Import Git Repository"**
3. Paste: `https://github.com/tariqalagha1/Scraper-gold-.git`
4. Vercel will auto-detect it's a Create React App

### 1.2 Configure Build Settings

- **Framework Preset:** Create React App ✓ (auto-selected)
- **Build Command:** `npm run build` ✓ (auto-detected)
- **Output Directory:** `frontend/build` → Change to `build`

### 1.3 Set Environment Variables

In Vercel dashboard, go to **Settings** → **Environment Variables** and add:

```env
REACT_APP_API_URL=https://scraper-api-prod.railway.app/api/v1
```

*(Replace `scraper-api-prod` with your Railway API domain)*

### 1.4 Deploy

Click **Deploy** button. Vercel will auto-build and deploy.

**Result:** Your frontend will be live at `https://your-project.vercel.app`

---

## 🚀 Step 2: Deploy Backend API to Railway

### 2.1 Create Railway Project

1. Go to **https://railway.app/dashboard**
2. Click **"Create New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect and select `https://github.com/tariqalagha1/Scraper-gold-.git`

### 2.2 Add Services

#### Service 1: PostgreSQL Database
1. In Railway project, click **"Add Service"** → **"Provision PostgreSQL"**
2. Railway auto-creates a Postgres instance
3. Copy the `DATABASE_URL` shown in the plugin settings

#### Service 2: Redis Cache
1. Click **"Add Service"** → **"Provision Redis"**
2. Copy the `REDIS_URL` from plugin settings

#### Service 3: API Server
1. Click **"Add Service"** → **"GitHub Repo"**
2. Select this repo again
3. In **Service Settings:**
   - **Service Name:** `api`
   - **Environment:** Select the repo
   - **Dockerfile:** `Dockerfile`
   - **Port:** `8000`

### 2.3 Set Environment Variables

In Railway, go to **Variables** and add:

```env
ENVIRONMENT=production
DEBUG=false
RELOAD=false
SECRET_KEY=replace-with-a-random-32-plus-char-token
DATABASE_URL=postgresql+asyncpg://[replace-with-your-postgres-url]
REDIS_URL=[replace-with-your-redis-url]
CORS_ORIGINS=https://your-project.vercel.app
PLAYWRIGHT_HEADLESS=true
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REQUEST_TIMEOUT_SECONDS=60
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

### 2.4 Deploy

1. In your API service, go to **Deployments**
2. Click **"Deploy"**
3. Wait for build to complete (5-10 min)

**Result:** Your API will be live at `https://scraper-api-prod.railway.app` (auto-generated domain)

---

## 🔗 Step 3: Connect Frontend to Backend

### 3.1 Get Backend URL

1. In Railway dashboard, open your API service
2. Copy the **Domain URL** (e.g., `https://scraper-api-prod.railway.app`)

### 3.2 Update Frontend Environment

1. Go to **Vercel Dashboard** → **Your Project** → **Settings**
2. Click **"Environment Variables"**
3. Update `REACT_APP_API_URL`:
   ```
   REACT_APP_API_URL=https://scraper-api-prod.railway.app/api/v1
   ```
4. Click **"Save"** → Vercel auto-redeploys

---

## 🗄️ Step 4: Database Setup

### Connect to Postgres

1. In Railway, open your Postgres service
2. Click **"Connect"** → Copy the connection string
3. In your local terminal, run:
   ```bash
   PGPASSWORD=your-password psql -h your-host -U your-user -d postgres
   ```

### Run Migrations

```bash
cd /Users/tariqalagha/Desktop/scraper-main/backend
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
alembic upgrade head
```

---

## 🔑 Generate Production Secret Key

**Copy-paste this in your terminal:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use the output as your `SECRET_KEY` in Railway environment variables.

---

## ✅ Verify Deployment

### Frontend
```bash
curl https://your-project.vercel.app
```

### Backend
```bash
curl https://scraper-api-prod.railway.app/api/v1/health
```

### API Connection
1. Go to your Vercel frontend URL
2. Open **DevTools** (F12) → **Console**
3. If no CORS errors, you're connected! ✅

---

## 🐛 Troubleshooting

### Vercel Build Fails
- **Solution:** Check build logs in Vercel dashboard. Usually missing `REACT_APP_API_URL`.

### Railway Deploy Fails
- **Solution:** Check logs in Railway dashboard. Usually missing `SECRET_KEY` or `DATABASE_URL`.

### API Returns 500
- **Solution:** Check Railway logs. Check that Redis and Postgres are connected.

### Frontend Can't Connect to API
- **Solution:** 
  1. Check CORS_ORIGINS in Railway matches your Vercel domain
  2. Verify `REACT_APP_API_URL` is set in Vercel
  3. Check browser DevTools for exact error

---

## 📊 Next Steps (Optional)

### Add Custom Domain

**Vercel:**
1. Settings → Domains → Add your domain
2. Follow Vercel's DNS instructions

**Railway:**
1. Service → Settings → Custom Domain
2. Enter your API subdomain (e.g., `api.yourdomain.com`)

### Monitor & Logs

- **Vercel:** Deployments tab shows all logs
- **Railway:** Service → Logs shows real-time output

### Scale Up

- **Vercel:** Automatic, no config needed
- **Railway:** Upgrade plan for more compute/memory

---

## 📝 Deployed URLs

After deployment, you'll have:

- **Frontend:** `https://your-project.vercel.app`
- **API:** `https://scraper-api-prod.railway.app`
- **Database:** Postgres on Railway (private)
- **Cache:** Redis on Railway (private)

---

**Need help?** Check:
- Vercel docs: https://vercel.com/docs
- Railway docs: https://docs.railway.app
