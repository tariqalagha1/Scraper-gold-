# Layer 1A P0 - Manual Verification Commands
# Use these commands to verify each remediation step

## Summary of Changes

### docker-compose.yml Changes:
- PostgreSQL: 5432 → 127.0.0.1:5432 (localhost only)
- Redis: 6379 → 127.0.0.1:6379 (localhost only)
- Backend: 8000 → 127.0.0.1:8001 (localhost only)
- Frontend: 3000 → 127.0.0.1:43102 (localhost only)
- Added healthcheck to backend
- Added env var interpolation (POSTGRES_PASSWORD, REDIS_PASSWORD, SCRAPER_BASE_URL)
- Redis now requires password authentication

### .env.production Changes:
- Strong secrets placeholders (replace with generated values)
- SCRAPER_BASE_URL configurable (for external Joulaa service)
- All database/Redis passwords use environment variables
- Secrets NOT committed to git

---

## Step 1: Generate Secrets

```bash
cd /Users/tariqalagha/Desktop/scraper-main

# Generate strong secrets
bash generate_secrets.sh

# Verify secrets were generated (should not show REPLACE_WITH)
grep -E "^(POSTGRES_PASSWORD|REDIS_PASSWORD|SECRET_KEY|API_KEY)=" .env.production
```

Expected output:
```
POSTGRES_PASSWORD=<32-char-hex>
REDIS_PASSWORD=<32-char-hex>
SECRET_KEY=<64-char-hex>
API_KEY=<32-char-hex>
```

---

## Step 2: Configure Smart Scraper URL

**Choose ONE option:**

### Option A: Smart Scraper as External Service (Joulaa)
```bash
# If running Joulaa on same host (separate docker-compose):
sed -i 's|SCRAPER_BASE_URL=.*|SCRAPER_BASE_URL=http://127.0.0.1:8000|' .env.production

# Verify
grep "SCRAPER_BASE_URL" .env.production
```

### Option B: Smart Scraper on Different Host
```bash
# If running on remote host:
sed -i 's|SCRAPER_BASE_URL=.*|SCRAPER_BASE_URL=http://smart-scraper-host.example.com:8000|' .env.production
```

### Option C: Disable Smart Scraper (Optional)
```bash
sed -i 's|SCRAPER_BASE_URL=.*|SCRAPER_BASE_URL=|' .env.production
```

---

## Step 3: Verify .env.production

```bash
# Check all secrets are strong (no REPLACE_WITH placeholders)
grep "REPLACE_WITH" .env.production && echo "❌ Placeholders found" || echo "✓ No placeholders"

# Verify key variables exist
echo "=== Key Variables ===" && \
grep -E "^(POSTGRES_PASSWORD|REDIS_PASSWORD|SECRET_KEY|API_KEY|SCRAPER_BASE_URL|DATABASE_URL|REDIS_URL)=" .env.production
```

Expected:
```
POSTGRES_PASSWORD=<strong-value>
REDIS_PASSWORD=<strong-value>
SECRET_KEY=<strong-value>
API_KEY=<strong-value>
SCRAPER_BASE_URL=http://... (or empty)
DATABASE_URL=postgresql+asyncpg://scraper:<password>@postgres:5432/scraper
REDIS_URL=redis://:<password>@redis:6379/0
```

---

## Step 4: Stop Current Containers & Clean

```bash
cd /Users/tariqalagha/Desktop/scraper-main

# Stop and remove containers
docker-compose down

# Remove old images (optional, saves time on rebuild)
docker rmi scraper-main-backend scraper-main-frontend 2>/dev/null || true

# Wait for cleanup
sleep 2
```

---

## Step 5: Rebuild & Start

```bash
# Rebuild with new Dockerfile and .env.production
docker-compose build --no-cache

# Start services
docker-compose up -d

# Wait for services to be healthy
sleep 10
```

---

## Step 6: Verify Network Isolation (P0 Requirement)

### PostgreSQL NOT exposed to 0.0.0.0
```bash
# Should show 127.0.0.1:5432 only
docker port scraper-postgres 5432

# Expected output:
# 127.0.0.1:5432

# Verify external access fails
nc -zv 0.0.0.0 5432 && echo "❌ EXPOSED" || echo "✓ Not exposed (expected)"
```

### Redis NOT exposed to 0.0.0.0
```bash
# Should show 127.0.0.1:6379 only
docker port scraper-redis 6379

# Expected output:
# 127.0.0.1:6379
```

### Backend NOT exposed to 0.0.0.0
```bash
# Should show 127.0.0.1:8001 only
docker port scraper-backend 8000

# Expected output:
# 127.0.0.1:8001
```

---

## Step 7: Verify Database Connectivity

```bash
# Test PostgreSQL health
docker exec scraper-postgres pg_isready -U scraper

# Expected: "accepting connections"

# Test Redis health with password
REDIS_PASS=$(grep "^REDIS_PASSWORD=" .env.production | cut -d= -f2)
docker exec scraper-redis redis-cli -a "$REDIS_PASS" ping

# Expected: "PONG"
```

---

## Step 8: Verify Backend Health

```bash
# Wait for backend to start (healthcheck: 30s start_period)
sleep 5

# Check health endpoint
curl -s http://127.0.0.1:8001/health | jq .

# Expected output:
# {
#   "status": "ok" or "degraded",
#   "services": {
#     "database": "ok",
#     "redis": "ok",
#     "scraper": "ok", "unavailable", or "unconfigured"
#   }
# }
```

---

## Step 9: Verify Secrets NOT Exposed in Containers

```bash
# Check backend environment - should NOT show dev/placeholder secrets
docker exec scraper-backend env | grep -E "(SECRET_KEY|API_KEY)" | grep -v "HEADER_NAME"

# Should show STRONG values, NOT:
# - "dev-api-key-change-me"
# - "your-super-secret-key"
# - "placeholder"

# Verify
docker exec scraper-backend env | grep "SECRET_KEY=" | grep -c "your-super-secret" && echo "❌ Placeholder found" || echo "✓ Real secret used"
```

---

## Step 10: Verify Redis Password Auth

```bash
# Test Redis auth works
REDIS_PASS=$(grep "^REDIS_PASSWORD=" .env.production | cut -d= -f2)

# Should succeed with correct password
docker exec scraper-redis redis-cli -a "$REDIS_PASS" ping
# Expected: "PONG"

# Should fail with wrong password
docker exec scraper-redis redis-cli -a "wrong-password" ping 2>&1 | grep -q "WRONGPASS" && echo "✓ Auth enforced" || echo "❌ No auth"
```

---

## Step 11: Verify Smart Scraper Connectivity

```bash
# Get SCRAPER_BASE_URL from .env.production
SCRAPER_URL=$(grep "^SCRAPER_BASE_URL=" .env.production | cut -d= -f2)

if [ -z "$SCRAPER_URL" ]; then
    echo "Smart Scraper URL not configured"
else
    echo "Testing Smart Scraper connectivity: $SCRAPER_URL"
    
    # If Joulaa is running locally:
    if [[ "$SCRAPER_URL" == *"127.0.0.1"* ]] || [[ "$SCRAPER_URL" == *"localhost"* ]]; then
        # Start Joulaa first:
        # cd /Users/tariqalagha/Desktop/new/scraper/Joulaa
        # docker-compose up -d
        
        curl -s "$SCRAPER_URL/health" | jq .
    else
        echo "Remote Smart Scraper - verify connectivity manually"
    fi
fi
```

---

## Step 12: Verify API Key Authentication

```bash
# Test with WRONG API key - should return 401
curl -X POST http://127.0.0.1:8001/api/v1/scrape \
  -H "X-API-Key: wrong-key" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://example.com","query":"test","location":"main","fields":["test"]}' \
  -w "\nHTTP Status: %{http_code}\n"

# Expected: HTTP Status 401
```

---

## Step 13: Verify Container Users (Optional - P0 doesn't change this)

```bash
# Note: Layer 1A does NOT change user privileges (P1 fix)
# Current: runs as root
docker exec scraper-backend id

# Expected for now: uid=0(root)
# (Will be fixed in Layer 1B)
```

---

## Step 14: Verify .env.production Not in Git

```bash
cd /Users/tariqalagha/Desktop/scraper-main

# Check if .env.production is in .gitignore
grep "^\.env\.production$" .gitignore && echo "✓ In .gitignore" || echo "❌ Not in .gitignore - add it!"

# Add if missing
echo ".env.production" >> .gitignore

# Verify git won't track it
git status | grep .env.production && echo "❌ Tracked by git!" || echo "✓ Not tracked"
```

---

## Step 15: Full Health Check

```bash
echo "=== Layer 1A P0 Verification ==="
echo ""

echo "[Network Isolation]"
echo "  PostgreSQL:" $(docker port scraper-postgres 5432 | grep "127.0.0.1" && echo "✓ Localhost only" || echo "❌ Exposed")
echo "  Redis:" $(docker port scraper-redis 6379 | grep "127.0.0.1" && echo "✓ Localhost only" || echo "❌ Exposed")
echo "  Backend:" $(docker port scraper-backend 8000 | grep "127.0.0.1" && echo "✓ Localhost only" || echo "❌ Exposed")

echo ""
echo "[Secrets]"
echo "  Secrets strong:" $(! grep "REPLACE_WITH\|dev-api-key\|your-super-secret" .env.production && echo "✓ Yes" || echo "❌ No")
echo "  .env.production ignored:" $(grep "^\.env\.production$" .gitignore && echo "✓ Yes" || echo "❌ No")

echo ""
echo "[Service Health]"
HEALTH=$(curl -s http://127.0.0.1:8001/health | jq -r '.status' 2>/dev/null)
echo "  Backend health: $HEALTH"

echo ""
echo "[Authentication]"
AUTH_TEST=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8001/api/v1/scrape \
  -H "X-API-Key: wrong" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://example.com","query":"test","location":"main","fields":["test"]}')
echo "  Wrong API key rejected:" $([ "$AUTH_TEST" = "401" ] || [ "$AUTH_TEST" = "403" ] && echo "✓ Yes (HTTP $AUTH_TEST)" || echo "❌ No (HTTP $AUTH_TEST)")
```

---

## Summary: What Changed

| Component | Before | After | Status |
|-----------|--------|-------|--------|
| PostgreSQL | 0.0.0.0:5432 | 127.0.0.1:5432 | ✓ Fixed |
| Redis | 0.0.0.0:6379 | 127.0.0.1:6379 | ✓ Fixed |
| Backend | 0.0.0.0:8001 | 127.0.0.1:8001 | ✓ Fixed |
| Redis Auth | None | Password required | ✓ Fixed |
| Secrets | Placeholder | Strong (generated) | ✓ Fixed |
| SCRAPER_BASE_URL | Hardcoded localhost:8003 | Configurable | ✓ Fixed |
| Database URLs | Hardcoded credentials | Environment vars | ✓ Fixed |
| Backend Healthcheck | None | 15s interval | ✓ Fixed |
| Git tracking | .env exposed | .env.production ignored | ✓ Fixed |

---

## Cleanup (If Something Goes Wrong)

```bash
# Stop everything
docker-compose down

# Remove volumes (careful - loses data!)
# docker volume rm scraper-main_postgres_data

# Reset docker-compose.yml to original
git checkout docker-compose.yml

# Keep .env.production for secrets (don't reset)
```

---

## Next Steps (Not Layer 1A)

- [ ] Layer 1B: Fix Dockerfiles (non-root users) - P1 issue
- [ ] Layer 2: CORS security fix - P1 issue
- [ ] Layer 3: Database migrations tracking - P1 issue
- [ ] Layer 4: WebSocket authentication - P1 issue
- [ ] Layer 5: Advanced security (P2 issues)
