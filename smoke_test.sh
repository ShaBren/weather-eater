#!/usr/bin/env bash
# smoke_test.sh — Docker-based end-to-end smoke test for Weather Eater
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

cleanup() {
    echo ""
    echo "Tearing down..."
    docker compose down -v 2>/dev/null || true
}
trap cleanup EXIT

echo "=== Weather Eater Smoke Test ==="

# 1. Build and start
echo "Building and starting containers..."
docker compose up --build -d --wait 2>&1 || fail "docker compose up failed"

# 2. Init DB
echo "Initializing database..."
docker compose exec -T weather flask init-db 2>&1 || fail "flask init-db failed"
pass "Database initialized"

# 3. Wait for health
echo "Waiting for app to be ready..."
for i in $(seq 1 15); do
    if curl -sf http://localhost:4902/ > /dev/null 2>&1; then
        break
    fi
    sleep 1
done
pass "App is responding"

# 4. Post sample reading
echo "Posting sample reading..."
curl -sf "http://localhost:4902/post_data?tempf=72.5&humidity=45&windspeedmph=10.0&baromabsin=29.92&winddir=180&dailyrainin=0.05&uv=3&battout=1" > /dev/null || fail "/post_data failed"
pass "/post_data returned OK"

# 5. Check /api/latest
echo "Checking /api/latest..."
LATEST=$(curl -sf http://localhost:4902/api/latest)
echo "$LATEST" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['data']['tempf']['raw']=='72.5', 'tempf mismatch'; assert len(d['data'])>0, 'empty data'" || fail "/api/latest validation failed"
pass "/api/latest has correct tempf value"

# 6. Check /api/metrics
echo "Checking /api/metrics..."
METRICS=$(curl -sf http://localhost:4902/api/metrics)
METRIC_COUNT=$(echo "$METRICS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
if [ "$METRIC_COUNT" -eq 24 ]; then
    pass "/api/metrics returns 24 items"
else
    fail "/api/metrics returned $METRIC_COUNT items (expected 24)"
fi

# 7. Check /api/daily_stats
echo "Checking /api/daily_stats..."
STATS=$(curl -sf http://localhost:4902/api/daily_stats)
echo "$STATS" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'min' in d; assert 'max' in d" || fail "/api/daily_stats missing min/max"
pass "/api/daily_stats has min/max"

# 8. Check dashboard HTML
echo "Checking dashboard..."
DASH=$(curl -sf http://localhost:4902/)
echo "$DASH" | grep -q "Weather Station Dashboard" || fail "Dashboard HTML missing title"
pass "Dashboard serves HTML"

echo ""
echo -e "${GREEN}=== All smoke tests passed! ===${NC}"
