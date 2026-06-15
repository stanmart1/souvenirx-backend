"""Shared Redis configuration for ARQ worker and queue."""
import ssl as ssl_module
from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.config import settings


def _build_ssl_context(cert_reqs: int) -> ssl_module.SSLContext:
    """
    Build an SSLContext for the given verification level.

    Python 3.12 note: ``ssl.create_default_context()`` produces a
    ``PROTOCOL_TLS_CLIENT`` context with ``check_hostname=True`` and
    ``verify_mode=CERT_REQUIRED`` baked in.  Attempting to mutate
    ``verify_mode`` on that context to ``CERT_NONE`` raises
    ``ssl.SSLError`` in some builds.  The safe pattern is to start
    with a *fresh* ``SSLContext(PROTOCOL_TLS_CLIENT)`` and configure
    it explicitly before any CA bundle is loaded.
    """
    if cert_reqs == ssl_module.CERT_NONE:
        # Self-signed / no-verification path.
        # Must set check_hostname=False BEFORE verify_mode on PROTOCOL_TLS_CLIENT.
        ctx = ssl_module.SSLContext(ssl_module.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl_module.CERT_NONE
        return ctx

    # Verified path — use the hardened default context.
    ctx = ssl_module.create_default_context()
    if cert_reqs == ssl_module.CERT_OPTIONAL:
        ctx.check_hostname = False
        ctx.verify_mode = ssl_module.CERT_OPTIONAL

    # Load explicit CA bundle when provided.
    if settings.redis_ssl_ca_certs:
        ctx.load_verify_locations(settings.redis_ssl_ca_certs)

    return ctx


def get_redis_settings() -> RedisSettings:
    """
    Parse Redis URL and return RedisSettings for ARQ.

    Uses the same SSL configuration logic as app.redis.build_redis_ssl_context()
    to ensure consistent SSL handling across the application.

    For self-signed certificates set the env var:
        REDIS_SSL_CERT_REQS=none
    """
    parsed = urlparse(settings.redis_url)
    database = int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0
    use_ssl = parsed.scheme == "rediss"

    if not use_ssl:
        return RedisSettings(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            database=database,
            password=parsed.password,
            ssl=False,
        )

    # Map config string to ssl.CERT_* constants.
    cert_reqs_map = {
        "none": ssl_module.CERT_NONE,
        "optional": ssl_module.CERT_OPTIONAL,
        "required": ssl_module.CERT_REQUIRED,
    }
    cert_reqs = cert_reqs_map.get(
        settings.redis_ssl_cert_reqs.lower(),
        ssl_module.CERT_REQUIRED,
    )

    ssl_ctx = _build_ssl_context(cert_reqs)

    # Load client certificate for mutual TLS if provided.
    if settings.redis_ssl_certfile:
        ssl_ctx.load_cert_chain(
            certfile=settings.redis_ssl_certfile,
            keyfile=settings.redis_ssl_keyfile or None,
        )

    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
        ssl=ssl_ctx,
    )
