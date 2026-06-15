import ssl
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings


def build_redis_ssl_context() -> Optional[ssl.SSLContext]:
    """Build an SSL context for Redis connections.

    Returns None when the Redis URL is not rediss://.

    Python 3.12 note: ssl.create_default_context() uses PROTOCOL_TLS_CLIENT
    which bakes in check_hostname=True and CERT_REQUIRED.  Changing verify_mode
    to CERT_NONE on that context is unreliable across builds.  For the
    no-verification (self-signed cert) path we start with a fresh
    SSLContext(PROTOCOL_TLS_CLIENT) and disable both flags explicitly.

    To allow self-signed certificates set:
        REDIS_SSL_CERT_REQS=none
    """
    if not settings.redis_url.startswith("rediss://"):
        return None

    cert_reqs_map = {
        "none": ssl.CERT_NONE,
        "optional": ssl.CERT_OPTIONAL,
        "required": ssl.CERT_REQUIRED,
    }
    cert_reqs = cert_reqs_map.get(settings.redis_ssl_cert_reqs.lower(), ssl.CERT_REQUIRED)

    if cert_reqs == ssl.CERT_NONE:
        # Self-signed / no-verification path.
        # check_hostname must be disabled BEFORE changing verify_mode.
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if settings.redis_ssl_certfile:
            ctx.load_cert_chain(
                certfile=settings.redis_ssl_certfile,
                keyfile=settings.redis_ssl_keyfile or None,
            )
        return ctx

    # Verified / optional path — use the hardened default context.
    ctx = ssl.create_default_context()
    if cert_reqs == ssl.CERT_OPTIONAL:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_OPTIONAL

    if settings.redis_ssl_ca_certs:
        ctx.load_verify_locations(settings.redis_ssl_ca_certs)

    if settings.redis_ssl_certfile:
        ctx.load_cert_chain(
            certfile=settings.redis_ssl_certfile,
            keyfile=settings.redis_ssl_keyfile or None,
        )

    return ctx


def _build_redis_kwargs() -> dict:
    kwargs: dict = {"decode_responses": True}
    ssl_ctx = build_redis_ssl_context()
    if ssl_ctx is not None:
        kwargs["ssl"] = ssl_ctx
    return kwargs


redis_client = aioredis.from_url(settings.redis_url, **_build_redis_kwargs())


async def get_redis() -> aioredis.Redis:
    return redis_client


async def check_rate_limit(key: str, max_requests: int, window_seconds: int = 60) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    try:
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, window_seconds)
        return current <= max_requests
    except Exception:
        return True


async def check_idempotency(key: str) -> bool:
    """Returns True if this is the first request (key is new), False if duplicate."""
    try:
        result = await redis_client.set(key, "1", nx=True, ex=3600)
        return result is not None
    except Exception:
        return True
