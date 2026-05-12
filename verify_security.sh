#!/bin/bash
# Security Verification Checklist - Run After Fixes Applied
# USAGE: bash verify_security.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((FAILED++))
    fi
}

echo "🔐 Security Verification Checklist"
echo "==================================="

# 1. Non-root user
echo -e "\n${YELLOW}[1] Container Users${NC}"
BACKEND_UID=$(docker exec scraper-backend id -u 2>/dev/null || echo "ERROR")
if [ "$BACKEND_UID" != "0" ] && [ "$BACKEND_UID" != "ERROR" ]; then
    test_result 0 "Backend runs as UID $BACKEND_UID (not root)"
else
    test_result 1 "Backend runs as root or error"
fi

FRONTEND_UID=$(docker exec scraper-frontend id -u 2>/dev/null || echo "ERROR")
if [ "$FRONTEND_UID" != "0" ] && [ "$FRONTEND_UID" != "ERROR" ]; then
    test_result 0 "Frontend runs as UID $FRONTEND_UID (not root)"
else
    test_result 1 "Frontend runs as root or error"
fi

# 2. Port bindings
echo -e "\n${YELLOW}[2] Network Exposure${NC}"
if docker port scraper-postgres 2>/dev/null | grep -q "127.0.0.1:5432"; then
    test_result 0 "PostgreSQL bound to 127.0.0.1:5432"
else
    test_result 1 "PostgreSQL not bound to 127.0.0.1"
fi

if docker port scraper-redis 2>/dev/null | grep -q "127.0.0.1:6379"; then
    test_result 0 "Redis bound to 127.0.0.1:6379"
else
    test_result 1 "Redis not bound to 127.0.0.1"
fi

# 3. Health check
echo -e "\n${YELLOW}[3] Service Health${NC}"
HEALTH=$(curl -s http://127.0.0.1:8001/health 2>/dev/null | jq -r '.status' 2>/dev/null || echo "ERROR")
if [ "$HEALTH" = "ok" ] || [ "$HEALTH" = "degraded" ]; then
    test_result 0 "Backend healthy: $HEALTH"
else
    test_result 1 "Backend not responding or unhealthy"
fi

# 4. Authentication
echo -e "\n${YELLOW}[4] API Key Authentication${NC}"
WRONG_KEY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8001/api/v1/scrape \
    -H "X-API-Key: wrong-api-key-12345" \
    -H "Content-Type: application/json" \
    -d '{"url":"http://example.com","query":"test","location":"main","fields":["test"]}' 2>/dev/null || echo "ERROR")

if [ "$WRONG_KEY_RESPONSE" = "401" ] || [ "$WRONG_KEY_RESPONSE" = "403" ]; then
    test_result 0 "Wrong API key rejected with HTTP $WRONG_KEY_RESPONSE"
else
    test_result 1 "Wrong API key accepted or error: $WRONG_KEY_RESPONSE"
fi

# 5. CORS Headers
echo -e "\n${YELLOW}[5] CORS Configuration${NC}"
CORS_HEADER=$(curl -s -I -H "Origin: http://evil.com" http://127.0.0.1:8001/health 2>/dev/null | grep -i "access-control-allow-origin" | wc -l)
if [ "$CORS_HEADER" -eq 0 ]; then
    test_result 0 "CORS credentials disabled (no Access-Control-Allow-Origin to unauthorized origin)"
else
    test_result 1 "CORS headers allow unauthorized origin"
fi

# 6. Security headers
echo -e "\n${YELLOW}[6] Security Headers${NC}"
SECURITY_HEADERS=$(curl -s -I http://127.0.0.1:8001/health 2>/dev/null | grep -E "X-Content-Type-Options|X-Frame-Options|Strict-Transport-Security" | wc -l)
if [ "$SECURITY_HEADERS" -ge 2 ]; then
    test_result 0 "Security headers present ($SECURITY_HEADERS found)"
else
    test_result 1 "Missing security headers (only $SECURITY_HEADERS found)"
fi

# 7. Database connectivity
echo -e "\n${YELLOW}[7] Database Health${NC}"
DB_CHECK=$(docker exec scraper-postgres pg_isready -U scraper 2>/dev/null | grep "accepting connections" | wc -l)
if [ "$DB_CHECK" -eq 1 ]; then
    test_result 0 "PostgreSQL accepting connections"
else
    test_result 1 "PostgreSQL not responding"
fi

# 8. Redis connectivity
echo -e "\n${YELLOW}[8] Redis Health${NC}"
REDIS_CHECK=$(docker exec scraper-redis redis-cli -a $(grep REDIS_PASSWORD .env.production | cut -d= -f2) ping 2>/dev/null | grep "PONG" | wc -l)
if [ "$REDIS_CHECK" -eq 1 ]; then
    test_result 0 "Redis responding"
else
    test_result 1 "Redis not responding"
fi

# 9. Alembic migration table
echo -e "\n${YELLOW}[9] Database Migrations${NC}"
ALEMBIC_CHECK=$(docker exec scraper-postgres psql -U scraper -d scraper -c "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version')" 2>/dev/null | grep -i true | wc -l)
if [ "$ALEMBIC_CHECK" -eq 1 ]; then
    test_result 0 "Alembic version table exists"
else
    test_result 1 "Alembic version table missing"
fi

# 10. Smart Scraper connectivity
echo -e "\n${YELLOW}[10] Smart Scraper Service${NC}"
SCRAPER_CHECK=$(docker exec scraper-backend curl -s http://scraper-smart:8000/health 2>/dev/null | grep -q '"status"' && echo "1" || echo "0")
if [ "$SCRAPER_CHECK" = "1" ]; then
    test_result 0 "Smart Scraper service reachable"
else
    test_result 1 "Smart Scraper service not responding"
fi

# 11. Secrets not hardcoded
echo -e "\n${YELLOW}[11] Secrets Management${NC}"
SECRETS_CHECK=$(docker exec scraper-backend env | grep -c "dev-api-key-change-me\|your-super-secret-key" || echo "0")
if [ "$SECRETS_CHECK" = "0" ]; then
    test_result 0 "No hardcoded placeholder secrets in environment"
else
    test_result 1 "Placeholder secrets found in container environment"
fi

# 12. SSRF protection
echo -e "\n${YELLOW}[12] SSRF Protection (Production Mode)${NC}"
SSRF_TEST=$(curl -s -X POST http://127.0.0.1:8001/api/v1/scrape \
    -H "X-API-Key: $(grep '^API_KEY=' .env.production | cut -d= -f2)" \
    -H "Content-Type: application/json" \
    -d '{"url":"http://127.0.0.1:6379","query":"test","location":"main","fields":["test"]}' 2>/dev/null | grep -i "security\|private\|blocked" | wc -l)

if [ "$SSRF_TEST" -ge 1 ]; then
    test_result 0 "SSRF protection active (blocks local IPs)"
else
    test_result 1 "SSRF protection may be disabled"
fi

# 13. Backend healthcheck configured
echo -e "\n${YELLOW}[13] Container Healthchecks${NC}"
BACKEND_HC=$(docker inspect scraper-backend | jq '.[] | .State.Health.Status' 2>/dev/null | grep -i "starting\|healthy" | wc -l)
if [ "$BACKEND_HC" -ge 1 ]; then
    test_result 0 "Backend healthcheck configured"
else
    test_result 1 "Backend healthcheck not found"
fi

# 14. .env.production not in git
echo -e "\n${YELLOW}[14] Secrets Version Control${NC}"
if grep -q "^.env.production$" .gitignore 2>/dev/null; then
    test_result 0 ".env.production in .gitignore"
else
    test_result 1 ".env.production not in .gitignore"
fi

# 15. Frontend production build
echo -e "\n${YELLOW}[15] Frontend Configuration${NC}"
FRONTEND_CMD=$(docker inspect scraper-frontend 2>/dev/null | jq -r '.[0].Config.Cmd[]' 2>/dev/null | grep -c "serve" || echo "0")
if [ "$FRONTEND_CMD" = "1" ]; then
    test_result 0 "Frontend running with serve (production mode)"
else
    test_result 1 "Frontend may be running in development mode"
fi

# Summary
echo -e "\n${YELLOW}==================================="
echo "Summary${NC}"
echo "  ${GREEN}Passed: $PASSED${NC}"
echo "  ${RED}Failed: $FAILED${NC}"

if [ "$FAILED" -eq 0 ]; then
    echo -e "\n${GREEN}✅ All security checks passed!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some security checks failed. Review issues above.${NC}"
    exit 1
fi
