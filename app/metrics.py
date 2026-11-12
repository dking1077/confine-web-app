from prometheus_client import Counter, Histogram, Gauge

# htt
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# cache
cache_operations_total = Counter(
    "cache_operations_total",
    "Cache operations",
    ["operation"],  # hit | miss | set | stale
)

# circuit Breaker
circuit_breaker_trips_total = Counter(
    "circuit_breaker_trips_total",
    "Circuit breaker trips",
    ["name"],
)

circuit_breaker_open = Gauge(
    "circuit_breaker_open",
    "Circuit breaker state (1 = open, 0 = closed)",
    ["name"],
)

# celery
celery_task_total = Counter(
    "celery_task_total",
    "Celery task results",
    ["task", "status"],  # success | failure | retry
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)


# helpers
def observe_cache(operation: str):
    cache_operations_total.labels(operation=operation).inc()


def observe_circuit_trip(name: str):
    circuit_breaker_trips_total.labels(name=name).inc()
    circuit_breaker_open.labels(name=name).set(1)


def observe_circuit_close(name: str):
    circuit_breaker_open.labels(name=name).set(0)