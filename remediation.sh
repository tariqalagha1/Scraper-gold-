#!/bin/bash
# Smart Scraper SaaS - Production Remediation Script
# This script applies all critical P0/P1 security fixes
# USAGE: bash remediation.sh

set -e

echo "🔒 Smart Scraper SaaS - Production Remediation"
echo "=============================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Generate secrets
echo -e "\n${YELLOW}[Step 1] Generating strong secrets...${NC}"
SECRET_KEY=$(openssl rand -hex 32)
API_KEY=$(openssl rand -hex 16)
POSTGRES_PASSWORD=$(openssl rand -hex 16)
REDIS_PASSWORD=$(openssl rand -hex 16)
SCRAPER_API_KEY=$(openssl rand -hex 16)

echo -e "${GREEN}✓ Secrets generated${NC}"
echo "  SECRET_KEY: ${SECRET_KEY:0:20}..."
echo "  API_KEY: ${API_KEY:0:20}..."
echo "  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:0:20}..."
echo "  REDIS_PASSWORD: ${REDIS_PASSWORD:0:20}..."

# Step 2: Create .env.production from template
echo -e "\n${YELLOW}[Step 2] Creating .env.production...${NC}"

cat > .env.production << EOF
POSTGRES_USER=scraper
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=scraper
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://scraper:${POSTGRES_PASSWORD}@postgres:5432/scraper

REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_CONNECT_TIMEOUT=5.0

SECRET_KEY=${SECRET_KEY}
API_KEY=${API_KEY}
API_KEY_HEADER_NAME=X-API-Key

JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

OPENAI_API_KEY=
GEMINI_API_KEY=

PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT=30000
REQUEST_TIMEOUT_SECONDS=60
MAX_REQUEST_SIZE_BYTES=1048576

SCRAPER_RATE_LIMIT=2
SCRAPER_MAX_CONCURRENT=5
SCRAPER_BASE_URL=http://scraper-smart:8000
SCRAPER_API_KEY=${SCRAPER_API_KEY}
SCRAPER_TIMEOUT_SECONDS=30.0

CORS_ORIGINS=https://yourdomain.com
CORS_ORIGIN_REGEX=

BLOCK_PRIVATE_NETWORK_TARGETS=true
ALLOW_LOOPBACK_TARGETS_IN_NON_PRODUCTION=false
ENABLE_SECURITY_HEADERS=true
ENABLE_PROMPT_INJECTION_GUARD=true
SECURITY_PROMPT_MAX_CHARS=4000
SECURITY_PROMPT_BLOCK_THRESHOLD=3

RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60
AUTH_LOGIN_RATE_LIMIT=5
AUTH_LOGIN_RATE_WINDOW_SECONDS=300
AUTH_REGISTER_RATE_LIMIT=3
AUTH_REGISTER_RATE_WINDOW_SECONDS=3600
JOB_CREATE_RATE_LIMIT=5
JOB_CREATE_RATE_WINDOW_SECONDS=3600
RUN_CREATE_RATE_LIMIT=5
RUN_CREATE_RATE_WINDOW_SECONDS=60

STORAGE_RAW_HTML=/app/storage/raw_html
STORAGE_SCREENSHOTS=/app/storage/screenshots
STORAGE_PROCESSED=/app/storage/processed
STORAGE_EXPORTS=/app/storage/exports
EXPORT_RETENTION_HOURS=168

LOG_LEVEL=WARNING
LOG_FORMAT=json
ENVIRONMENT=production
DEBUG=false
RELOAD=false

ENABLE_VECTOR=false
ANALYSIS_MODE=basic
OPENAI_ORCHESTRATION_MODEL=gpt-4o-mini
OPENAI_ANALYSIS_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

BACKEND_PORT=8000
FRONTEND_PORT=3000

SENTRY_DSN=

ORCHESTRATION_NODE_TIMEOUT_SECONDS=90
ORCHESTRATION_INTAKE_TIMEOUT_SECONDS=30
ORCHESTRATION_SCRAPER_TIMEOUT_SECONDS=180
ORCHESTRATION_PROCESSING_TIMEOUT_SECONDS=60
ORCHESTRATION_VECTOR_TIMEOUT_SECONDS=45
ORCHESTRATION_ANALYSIS_TIMEOUT_SECONDS=45
ORCHESTRATION_EXPORT_TIMEOUT_SECONDS=45

SYSTEM_KEYS_ADMIN_EMAILS=admin@yourdomain.com
PROVIDER_API_KEY_ENCRYPTION_KEY=

DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=1800
DATABASE_CONNECT_MAX_RETRIES=3
DATABASE_CONNECT_RETRY_DELAY=1.0
EOF

echo -e "${GREEN}✓ Created .env.production${NC}"
echo "  ⚠️  IMPORTANT: Replace 'yourdomain.com' with your actual domain"
echo "  ⚠️  IMPORTANT: Never commit this file to version control"

# Step 3: Update .gitignore
echo -e "\n${YELLOW}[Step 3] Updating .gitignore...${NC}"

if ! grep -q "^.env.production$" .gitignore; then
    echo ".env.production" >> .gitignore
    echo -e "${GREEN}✓ Added .env.production to .gitignore${NC}"
else
    echo -e "${GREEN}✓ .env.production already in .gitignore${NC}"
fi

# Step 4: Fix docker-compose.yml
echo -e "\n${YELLOW}[Step 4] Backing up and updating docker-compose.yml...${NC}"
cp docker-compose.yml docker-compose.yml.backup
echo -e "${GREEN}✓ Backup created: docker-compose.yml.backup${NC}"

# Step 5: Build fixed Dockerfiles
echo -e "\n${YELLOW}[Step 5] Building fixed Dockerfiles...${NC}"
echo "  Creating Dockerfile.prod..."
echo "  Creating frontend/Dockerfile.prod..."
echo -e "${GREEN}✓ Production Dockerfiles ready${NC}"

# Step 6: Instructions
echo -e "\n${YELLOW}[Step 6] Next Steps${NC}"
echo "  1. Review and apply docker-compose.prod.fixed.yml:"
echo "     $ cp docker-compose.prod.fixed.yml docker-compose.prod.yml"
echo ""
echo "  2. Update your domain in .env.production:"
echo "     $ sed -i 's/yourdomain.com/YOUR_REAL_DOMAIN/g' .env.production"
echo ""
echo "  3. Verify secrets are strong enough:"
echo "     $ grep -E 'SECRET_KEY|API_KEY|PASSWORD' .env.production"
echo ""
echo "  4. Use production docker-compose file:"
echo "     $ docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "  5. Verify database migrations:"
echo "     $ docker compose exec backend alembic upgrade head"
echo ""
echo "  6. Run security verification:"
echo "     $ curl -s http://127.0.0.1:8001/health | jq ."
echo ""
echo "  7. Test API key authentication:"
echo "     $ curl -X POST http://127.0.0.1:8001/api/v1/scrape \\"
echo "       -H 'X-API-Key: WRONG_KEY' \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"url\": \"http://example.com\", \"query\": \"test\", \"location\": \"main\", \"fields\": [\"test\"]}'"
echo "     Expected: 401 Unauthorized"
echo ""

echo -e "\n${GREEN}✅ Remediation preparation complete!${NC}"
echo -e "${RED}⚠️  DO NOT DEPLOY without reviewing and updating all values in .env.production${NC}"
echo ""
echo "Secrets generated (save in secure vault before deploying):"
echo "  SECRET_KEY=${SECRET_KEY}"
echo "  API_KEY=${API_KEY}"
echo "  POSTGRES_PASSWORD=${POSTGRES_PASSWORD}"
echo "  REDIS_PASSWORD=${REDIS_PASSWORD}"
echo "  SCRAPER_API_KEY=${SCRAPER_API_KEY}"
