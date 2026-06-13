import logging
from urllib.parse import urlparse

import ssl as ssl_module
from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings

logger = logging.getLogger("souvenirx.queue")


def _redis_settings_from_url() -> RedisSettings:
    parsed = urlparse(settings.redis_url)
    database = int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0
    use_ssl = parsed.scheme == "rediss"
    ssl_ctx = None
    if use_ssl:
        ssl_ctx = ssl_module.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl_module.CERT_NONE
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
        ssl=ssl_ctx,
    )


async def get_arq_pool():
    redis_settings = _redis_settings_from_url()
    return await create_pool(redis_settings)


_pool = None


async def enqueue(func_name: str, **kwargs):
    global _pool
    if _pool is None:
        _pool = await get_arq_pool()
        logger.info("ARQ pool created for enqueuing jobs")
    await _pool.enqueue_job(func_name, **kwargs)
    logger.debug("Enqueued job %s with kwargs=%s", func_name, kwargs)
