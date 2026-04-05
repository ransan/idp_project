from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import HTTPException

from app.config import settings

_redis_client = None


def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def check_rate_limit(client_id: str, limit: int = 100) -> None:
    """
    Sliding window: max {limit} requests per hour per client.
    Uses Redis sorted sets for efficient counting.
    """
    r = _get_redis()
    key = f"ratelimit:{client_id}"
    now = datetime.now(timezone.utc).timestamp()
    window = 3600  # 1 hour

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)  # prune old entries
    pipe.zadd(key, {f"{now}:{id(pipe)}": now})  # add current (unique member)
    pipe.zcard(key)  # count entries in window
    pipe.expire(key, window)  # auto-cleanup
    results = await pipe.execute()

    count = results[2]
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {limit} requests/hour.",
            headers={"Retry-After": "60"},
        )
