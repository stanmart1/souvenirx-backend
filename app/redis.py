import ssl
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings


def build_redis_ssl_context() -> Optional[ssl.SSLContext]:
    """Build an SSLContext for Redis connections.

    Retained for backward compatibility / testing.  The live connection
    client (redis_client below) uses _build_redis_kwargs() which passes
    the individual ssl_* params to aioredis.from_url() instead — redis-py
    5.x SSLConnection does not accept an SSLContext object directly.

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
    """Build connection kwargs for aioredis.from_url().

    redis-py 5.x note: SSLConnection.__init__() does NOT accept 'ssl' or
    'ssl_context' kwargs.  Unknown kwargs flow through **kwargs all the way to
    AbstractConnection.__init__() which raises:
        TypeError: AbstractConnection.__init__() got an unexpected keyword
                   argument 'ssl'
    The correct approach is to pass the named SSL params (ssl_cert_reqs,
    ssl_ca_certs, etc.) which SSLConnection accepts explicitly.
    The rediss:// URL scheme already tells redis-py to use SSLConnection;
    no separate 'ssl=True' flag is needed.
    """
    kwargs: dict = {"decode_responses": True}
    if not settings.redis_url.startswith("rediss://"):
        return kwargs

    # Map our config → redis-py SSLConnection params.
    # For self-signed certificates set REDIS_SSL_CERT_REQS=none.
    kwargs["ssl_cert_reqs"] = settings.redis_ssl_cert_reqs.lower()
    if settings.redis_ssl_ca_certs:
        kwargs["ssl_ca_certs"] = settings.redis_ssl_ca_certs
    if settings.redis_ssl_certfile:
        kwargs["ssl_certfile"] = settings.redis_ssl_certfile
    if settings.redis_ssl_keyfile:
        kwargs["ssl_keyfile"] = settings.redis_ssl_keyfile
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
