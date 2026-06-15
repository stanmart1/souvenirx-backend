import logging
import atexit

from arq import create_pool

from app.tasks.redis_config import get_redis_settings

logger = logging.getLogger("souvenirx.queue")


async def get_arq_pool():
    redis_settings = get_redis_settings()
    return await create_pool(redis_settings)


_pool = None


async def enqueue(func_name: str, **kwargs):
    global _pool
    if _pool is None:
        _pool = await get_arq_pool()
        logger.info("ARQ pool created for enqueuing jobs")
    await _pool.enqueue_job(func_name, **kwargs)
    logger.debug("Enqueued job %s with kwargs=%s", func_name, kwargs)


async def close_arq_pool():
    """Close the ARQ pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.close()
        logger.info("ARQ pool closed")
        _pool = None


def _sync_close_pool():
    """Synchronous wrapper for atexit hook."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(close_arq_pool())
        else:
            loop.run_until_complete(close_arq_pool())
    except Exception as e:
        logger.warning("Failed to close ARQ pool on exit: %s", e)


atexit.register(_sync_close_pool)
