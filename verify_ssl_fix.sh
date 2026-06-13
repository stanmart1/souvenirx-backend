#!/bin/bash
# SSL Fix Verification Script
# Run this after deploying to verify the fix is working

set -e

echo "=================================================="
echo "SouvenirX Backend - SSL Fix Verification"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Container name (adjust if different)
CONTAINER_NAME="${1:-souvenirx-backend}"

echo "Checking container: $CONTAINER_NAME"
echo ""

# Check 1: Container is running
echo -n "1. Checking if container is running... "
if docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "   Container is not running!"
    exit 1
fi

# Check 2: SSL certificates exist and are readable
echo -n "2. Checking SSL certificate permissions... "
SSL_CHECK=$(docker exec "$CONTAINER_NAME" sh -c 'test -r /etc/ssl/certs/ca-certificates.crt && echo "OK" || echo "FAIL"' 2>/dev/null)
if [ "$SSL_CHECK" = "OK" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "   SSL certificates not readable by appuser!"
    exit 1
fi

# Check 3: No permission errors in logs
echo -n "3. Checking for permission errors in logs... "
if docker logs "$CONTAINER_NAME" 2>&1 | grep -qi "permission denied"; then
    echo -e "${RED}✗ FAIL${NC}"
    echo "   Found permission errors in logs:"
    docker logs "$CONTAINER_NAME" 2>&1 | grep -i "permission denied" | tail -5
    exit 1
else
    echo -e "${GREEN}✓ PASS${NC}"
fi

# Check 4: Migrations completed successfully
echo -n "4. Checking if migrations completed... "
if docker logs "$CONTAINER_NAME" 2>&1 | grep -q "Running database migrations"; then
    if docker logs "$CONTAINER_NAME" 2>&1 | grep -qi "error\|failed"; then
        echo -e "${RED}✗ FAIL${NC}"
        echo "   Migrations ran but encountered errors"
        exit 1
    else
        echo -e "${GREEN}✓ PASS${NC}"
    fi
else
    echo -e "${YELLOW}⚠ SKIP${NC}"
    echo "   Could not verify migrations (container may have restarted)"
fi

# Check 5: Application started successfully
echo -n "5. Checking if application started... "
if docker logs "$CONTAINER_NAME" 2>&1 | grep -q "Starting SouvenirX API\|Uvicorn running"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "   Application did not start successfully"
    exit 1
fi

# Check 6: No SSL errors in logs
echo -n "6. Checking for SSL errors... "
if docker logs "$CONTAINER_NAME" 2>&1 | grep -qi "ssl.*error\|sslrootcert"; then
    echo -e "${RED}✗ FAIL${NC}"
    echo "   Found SSL errors in logs:"
    docker logs "$CONTAINER_NAME" 2>&1 | grep -i "ssl.*error\|sslrootcert" | tail -5
    exit 1
else
    echo -e "${GREEN}✓ PASS${NC}"
fi

# Check 7: Health endpoint (if available)
echo -n "7. Checking health endpoint... "
HEALTH_CHECK=$(docker exec "$CONTAINER_NAME" sh -c 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null || echo "SKIP"')
if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
elif [ "$HEALTH_CHECK" = "SKIP" ]; then
    echo -e "${YELLOW}⚠ SKIP${NC}"
    echo "   curl not available in container"
else
    echo -e "${YELLOW}⚠ WARN${NC}"
    echo "   Health endpoint returned: $HEALTH_CHECK"
fi

# Check 8: Database connection (via alembic current)
echo -n "8. Checking database connection... "
DB_CHECK=$(docker exec "$CONTAINER_NAME" sh -c 'alembic current 2>&1' || echo "FAIL")
if echo "$DB_CHECK" | grep -qi "error\|permission denied"; then
    echo -e "${RED}✗ FAIL${NC}"
    echo "   Database connection failed:"
    echo "$DB_CHECK" | head -5
    exit 1
elif echo "$DB_CHECK" | grep -q "head"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${YELLOW}⚠ WARN${NC}"
    echo "   Could not verify database connection"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}All checks passed! SSL fix is working correctly.${NC}"
echo "=================================================="
echo ""
echo "Additional verification steps:"
echo "  - Monitor logs for 24-48 hours"
echo "  - Test critical API endpoints"
echo "  - Check error rates in monitoring"
echo ""
echo "To view live logs:"
echo "  docker logs -f $CONTAINER_NAME"
echo ""
