import json
import os
import redis
import logging

logger = logging.getLogger(__name__)

# DB 0 → default (Celery broker/backend)
# DB 1 → rate limiting
# DB 2 → cache
# ttl=43200 # 12 hours in seconds
# make key -> check get cache - > miss set cache or api return

redis_search_cache = redis.Redis.from_url(
    os.getenv("REDIS_URL_CACHE", "redis://redis:6379/2"),
    decode_responses=True
)


# search cache key, get, set, delete
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
        return None
    try:
        logger.info("search cache hit for key: %s", key)
        return json.loads(cached)
    except json.JSONDecodeError:
        return None


def cache_set(key, value, ttl=43200):
    redis_search_cache.setex(key, ttl, json.dumps([obj for obj in value]))
    logger.info("search cache set for key: %s", key)


def cache_delete(key):
    redis_search_cache.delete(key)