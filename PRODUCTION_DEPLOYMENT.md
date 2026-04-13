# Production Deployment Guide

This guide covers the complete production deployment setup for the Smart Scraper Platform.

## 🚀 Quick Start

Run the automated setup script:

```bash
./setup-production.sh
```

This script will guide you through setting up all production infrastructure components.

## 📋 Manual Setup (Alternative)

If you prefer manual setup, follow these steps:

### 1. Environment Configuration

Copy the production environment template:

```bash
cp .env.production.example .env.production
```

Fill in the required values in `.env.production`.

### 2. Database Setup (Supabase)

1. Create a new project at [supabase.com](https://supabase.com)
2. Run the database migrations from `backend/app/db/migrations/`
3. Configure Row Level Security (RLS) policies
4. Get your connection URL and service role key

### 3. Redis Setup (Upstash)

1. Create a Redis database at [upstash.com](https://upstash.com)
2. Get the Redis URL for your database

### 4. Authentication Setup (Clerk)

1. Create an application at [clerk.com](https://clerk.com)
2. Configure authentication flows
3. Get your publishable key and secret key

### 5. Monitoring Setup (Sentry)

1. Create a Sentry account at [sentry.io](https://sentry.io)
2. Create two projects: one for frontend, one for backend
3. Get the DSN keys for both projects

### 6. Frontend Deployment (Vercel)

```bash
cd frontend
npx vercel login
npx vercel --prod
```

Set the following environment variables in Vercel:

- `REACT_APP_CLERK_PUBLISHABLE_KEY`
- `REACT_APP_SENTRY_DSN`
- `REACT_APP_API_URL` (your backend URL)

### 7. Backend Deployment (Railway)

1. Create a Railway project at [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Railway will automatically detect the `railway.toml` configuration
4. Set environment variables in Railway dashboard

## 🔧 Environment Variables

### Backend (.env.production)

```bash
# Core
ENVIRONMENT=production
DEBUG=false
RELOAD=false

# Security
SECRET_KEY=<32-char-random-string>
API_KEY=<production-api-key>

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://default:pass@host:6379

# AI Services
OPENAI_API_KEY=<your-openai-key>

# Monitoring
SENTRY_DSN=<sentry-backend-dsn>

# Authentication
CLERK_SECRET_KEY=<clerk-secret-key>
```

### Frontend (Vercel Environment Variables)

```bash
REACT_APP_CLERK_PUBLISHABLE_KEY=<clerk-publishable-key>
REACT_APP_SENTRY_DSN=<sentry-frontend-dsn>
REACT_APP_API_URL=<backend-url>
```

## 🏗️ Infrastructure Components

### Hosting
- **Frontend**: Vercel
- **Backend**: Railway

### Database
- **Primary**: Supabase PostgreSQL
- **Cache**: Upstash Redis

### Authentication
- **Provider**: Clerk

### Monitoring
- **Error Tracking**: Sentry
- **Alerts**: Sentry notifications

### Rate Limiting
- **Distributed**: Redis-based rate limiting

## 🧪 Validation Checklist

After deployment, verify:

### Hosting ✅
- [ ] Frontend URL accessible
- [ ] SSL certificate active
- [ ] Custom domain configured (optional)

### Database ✅
- [ ] Connection successful
- [ ] Migrations applied
- [ ] Read/write operations work
- [ ] Backup configured

### Authentication ✅
- [ ] Login flow works
- [ ] Protected routes secured
- [ ] Session management active
- [ ] Token refresh working

### Monitoring ✅
- [ ] Sentry receiving events
- [ ] Error alerts configured
- [ ] Performance monitoring active

### Rate Limiting ✅
- [ ] Requests properly limited
- [ ] Distributed across instances
- [ ] Burst protection active

## 🚨 Troubleshooting

### Common Issues

**Build Failures**
- Check environment variables are set correctly
- Verify all dependencies are installed
- Check build logs for specific errors

**Database Connection Issues**
- Verify DATABASE_URL format
- Check firewall settings
- Ensure SSL is properly configured

**Authentication Problems**
- Verify Clerk keys are correct
- Check CORS configuration
- Ensure session cookies are set

**Rate Limiting Issues**
- Check Redis connectivity
- Verify rate limit configurations
- Monitor Redis memory usage

## 📊 Monitoring & Maintenance

### Health Checks
- Backend: `GET /api/v1/health/full`
- Database connectivity monitoring
- Redis connectivity monitoring

### Backup Strategy
- Database: Daily automated backups via Supabase
- Redis: Upstash managed backups
- Application logs: Centralized via Railway

### Scaling Considerations
- Railway handles horizontal scaling automatically
- Redis provides distributed caching
- Supabase handles database scaling

## 🔒 Security Considerations

- All secrets stored as environment variables
- SSL/TLS enabled on all endpoints
- CORS properly configured
- Rate limiting prevents abuse
- Authentication required for sensitive operations

## 📞 Support

For deployment issues:
1. Check this guide first
2. Review service-specific documentation
3. Check application logs
4. Contact the development team

---

**Status**: Production deployment ready ✅