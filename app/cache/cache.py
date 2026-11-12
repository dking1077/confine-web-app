import json
import os
import time
import redis
import logging
from app.metrics import observe_cache

logger = logging.getLogger(__name__)

# DB 0 → default (Celery broker/backend)
# DB 1 → rate limiting
# DB 2 → cache
# ttl=43200 # 12 hours in seconds

redis_search_cache = redis.Redis.from_url(
    os.getenv("REDIS_URL_CACHE", "redis://redis:6379/2"),
    decode_responses=True
)


def cache_keys(artist_input, track_input):
    if track_input:
        key = f'{artist_input}:{track_input}'
    else:
        key = f'{artist_input}'
    return key


def cache_get(key):
    cached = redis_search_cache.get(key)
    if not cached:
        logger.info("search cache miss for key: %s", key)
        observe_cache("miss")
        return None
    try:
        logger.info("search cache hit for key: %s", key)
        observe_cache("hit")
        return json.loads(cached)
    except json.JSONDecodeError:
        observe_cache("miss")
        return None


def cache_set(key, value, ttl=43200, stale_ttl=604800):
    payload = json.dumps([obj for obj in value])
    redis_search_cache.setex(key, ttl, payload)
    redis_search_cache.setex(f"stale:{key}", stale_ttl, payload)
    logger.info("search cache set for key: %s", key)
    observe_cache("set")


def cache_get_stale(key):
    cached = redis_search_cache.get(f"stale:{key}")
    if cached:
        observe_cache("stale")
        return json.loads(cached)
    return None


def cache_delete(key):
    redis_search_cache.delete(key)


def acquire_lock(key, ttl=60):
    lock = redis_search_cache.lock(f"lock:{key}", timeout=ttl, blocking=False)
    return lock if lock.acquire() else None


def release_lock(lock):
    try:
        lock.release()
    except redis.exceptions.LockError:
        logger.warning("lock expired before release")


def wait_for_cache(key, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        data = cache_get(key)
        if data:
            return data
        time.sleep(0.25)
    return None