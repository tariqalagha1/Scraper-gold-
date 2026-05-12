#!/bin/bash
# Layer 1A P0 - Generate Strong Secrets
# Usage: bash generate_secrets.sh

set -e

echo "🔐 Generating Strong Secrets for Layer 1A P0"
echo "==========================================="

# Generate secrets
POSTGRES_PASSWORD=$(openssl rand -hex 16)
REDIS_PASSWORD=$(openssl rand -hex 16)
SECRET_KEY=$(openssl rand -hex 32)
API_KEY=$(openssl rand -hex 16)

echo ""
echo "Generated Secrets (save in secure location - vault, env vars, K8s secrets):"
echo ""
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
echo "SECRET_KEY=$SECRET_KEY"
echo "API_KEY=$API_KEY"
echo ""

echo "Updating .env.production with generated secrets..."
echo ""

# Update .env.production
sed -i.bak "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" .env.production
sed -i.bak "s|REPLACE_WITH_STRONG_32_CHAR_PASSWORD|$POSTGRES_PASSWORD|g" .env.production
sed -i.bak "s|REPLACE_WITH_STRONG_REDIS_PASSWORD|$REDIS_PASSWORD|g" .env.production
sed -i.bak "s|REPLACE_WITH_32_CHAR_RANDOM_STRING|$SECRET_KEY|g" .env.production
sed -i.bak "s|REPLACE_WITH_16_CHAR_RANDOM_STRING|$API_KEY|g" .env.production

echo "✓ Secrets updated in .env.production"
echo ""
echo "⚠️  IMPORTANT:"
echo "  1. Store secrets in your vault (Kubernetes secrets, AWS Secrets Manager, HashiCorp Vault, etc.)"
echo "  2. Never commit .env.production to git"
echo "  3. Verify: grep -E 'PASSWORD|SECRET_KEY|API_KEY' .env.production"
echo ""

# Show what was updated
echo "Verification - Current secrets in .env.production:"
grep -E "^(POSTGRES_PASSWORD|REDIS_PASSWORD|SECRET_KEY|API_KEY)=" .env.production | head -4

echo ""
echo "✓ Layer 1A P0 secrets generated"
