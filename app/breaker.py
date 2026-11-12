import os
import redis
from app.errors import ApiError
from app.metrics import observe_circuit_trip, observe_circuit_close

redis_breaker = redis.Redis.from_url(os.getenv("REDIS_URL_BREAKER", "redis://redis:6379/5"), decode_responses=True)

THRESHOLD = 5
WINDOW = 60
COOLDOWN = 30


class CircuitOpenError(ApiError):
    def __init__(self, name, retry_after=COOLDOWN):
        super().__init__(
            code="UPSTREAM_UNAVAILABLE",
            message=f"{name} is temporarily unavailable.",
            status_code=503,
            details={"retry_after": retry_after},
        )


def is_open(name):
    return bool(redis_breaker.exists(f"breaker:{name}:open"))


def trip(name, seconds=COOLDOWN):
    redis_breaker.set(f"breaker:{name}:open", 1, ex=seconds)
    observe_circuit_trip(name)


def record_failure(name):
    key = f"breaker:{name}:fails"
    fails = redis_breaker.incr(key)
    if fails == 1:
        redis_breaker.expire(key, WINDOW)
    if fails >= THRESHOLD:
        trip(name)


def record_success(name):
    redis_breaker.delete(f"breaker:{name}:fails")
    # Only close the gauge if the breaker is actually closed
    if not is_open(name):
        observe_circuit_close(name)


def retry_after(header):
    try:
        return min(int(header), 120)
    except (TypeError, ValueError):
        return COOLDOWN