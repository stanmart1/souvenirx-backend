#!/bin/bash
# start_worker.sh — entrypoint for the ARQ worker container.
#
# Waits for Redis to become reachable before handing off to arq so the
# container does not die immediately and trigger exponential back-off.
#
# Self-signed / SSL config is controlled by env vars — see .env.example:
#   REDIS_URL=rediss://<host>:<port>/0
#   REDIS_SSL_CERT_REQS=none          # skip cert verification for self-signed

set -euo pipefail

REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
MAX_WAIT=60   # seconds before giving up
SLEEP=2

echo "Starting SouvenirX ARQ Worker..."
echo "Redis URL: ${REDIS_URL}"

# ---------------------------------------------------------------------------
# Wait for Redis to be reachable
# Parses host:port from REDIS_URL using Python (already in the image) so it
# correctly handles both redis:// and rediss:// schemes.
# ---------------------------------------------------------------------------
_redis_host_port() {
    python3 - <<'EOF'
import sys, os
from urllib.parse import urlparse
u = urlparse(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
print(u.hostname or "localhost")
print(u.port or 6379)
EOF
}

read -r REDIS_HOST REDIS_PORT < <(_redis_host_port)

echo "Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT} (timeout ${MAX_WAIT}s)..."
waited=0
until python3 -c "
import socket, sys
try:
    s = socket.create_connection(('${REDIS_HOST}', ${REDIS_PORT}), timeout=2)
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    if [ "$waited" -ge "$MAX_WAIT" ]; then
        echo "ERROR: Redis at ${REDIS_HOST}:${REDIS_PORT} did not become reachable within ${MAX_WAIT}s." >&2
        exit 1
    fi
    echo "  Redis not ready yet — retrying in ${SLEEP}s... (${waited}/${MAX_WAIT}s elapsed)"
    sleep "$SLEEP"
    waited=$((waited + SLEEP))
done

echo "Redis is reachable. Launching ARQ worker..."
exec arq app.arq_worker.WorkerSettings
