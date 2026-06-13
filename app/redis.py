import ssl
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings


def build_redis_ssl_context() -> Optional[ssl.SSLContext]:
    """Build an SSL context for Redis connections.

    Returns None when the Redis URL is not rediss://.
    """
    if not settings.redis_url.startswith("rediss://"):
        return None

    cert_reqs_map = {
        "none": ssl.CERT_NONE,
        "optional": ssl.CERT_OPTIONAL,
        "required": ssl.CERT_REQUIRED,
    }
    cert_reqs = cert_reqs_map.get(settings.redis_ssl_cert_reqs.lower(), ssl.CERT_REQUIRED)

    ctx = ssl.create_default_context()
    ctx.check_hostname = cert_reqs == ssl.CERT_REQUIRED
    ctx.verify_mode = cert_reqs

    if settings.redis_ssl_ca_certs:
        ctx.load_verify_locations(settings.redis_ssl_ca_certs)
    elif cert_reqs != ssl.CERT_NONE:
        try:
            ctx.load_default_certs()
        except Exception:
            pass

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
