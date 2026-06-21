# syntax=docker/dockerfile:1

# Single-stage build.
#
# The previous multi-stage build (builder + COPY --from=builder /install /usr/local)
# failed on build nodes with limited disk space because the ML dependencies
# (rembg, onnxruntime, scipy, opencv, llvmlite, …) produce a ~1 GB /install
# directory that then has to be duplicated into the runtime layer via COPY.
# Installing directly in the runtime stage avoids that double storage.
FROM python:3.12-slim

WORKDIR /app

# Install runtime system packages and build-essential (temporary — needed to
# compile C extensions for asyncpg, argon2-cffi, cryptography, etc.).
# build-essential is purged in the same RUN layer so it doesn't bloat the
# final image, while still keeping the pip install cache-friendly by copying
# requirements.txt before the application code.
RUN apt-get update && apt-get install -y --no-install-recommends \
    util-linux \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set Python path so Alembic can find app module
ENV PYTHONPATH=/app

# Copy application code
COPY . .

# Create upload directories
RUN mkdir -p /app/uploads/products /app/uploads/proofs /app/uploads/logos

# Make start script executable
RUN chmod +x /app/start.sh

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

# Fix SSL certificate permissions at build time
# CA certificates are public trust anchors and should be world-readable
RUN chmod -R a+r /etc/ssl/certs 2>/dev/null || true && \
    chmod a+r /etc/ssl/certs/ca-certificates.crt 2>/dev/null || true

# Entrypoint: chown any host bind mounts (no-op for Docker-named volumes,
# where Docker manages permissions), then drop to appuser via setpriv
# before exec'ing the supplied command.
COPY --chmod=755 <<'EOF' /entrypoint.sh
#!/bin/bash
set -e
# Fix ownership of /app/uploads in case a host bind mount overrode the
# build-time ownership. Idempotent — safe to run on every start.
chown -R appuser:appuser /app/uploads 2>/dev/null || true
# Ensure SSL certificates remain readable (in case they were overridden)
# CA certificates are public trust anchors and should be world-readable
chmod -R a+r /etc/ssl/certs 2>/dev/null || true
chmod a+r /etc/ssl/certs/ca-certificates.crt 2>/dev/null || true
exec setpriv --reuid=$(id -u appuser) --regid=$(id -g appuser) --init-groups -- "$@"
EOF

EXPOSE 8000

CMD ["/entrypoint.sh", "/app/start.sh"]
