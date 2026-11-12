import time
import uuid
import logging
from flask import g, request, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.metrics import http_requests_total, http_request_duration_seconds

logger = logging.getLogger(__name__)


def get_request_id():
    request_id = getattr(g, "request_id", None)
    if request_id:
        return request_id
    return "-"


def log_extra():
    return {"request_id": get_request_id()}


def init_observability(app):
    @app.before_request
    def bind_request_id():
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        g.request_id = request_id
        request._start_time = time.perf_counter()

    @app.after_request
    def attach_request_id_and_metrics(response):
        # Request ID
        response.headers["X-Request-ID"] = get_request_id()

        # Metrics
        if hasattr(request, "_start_time"):
            duration = time.perf_counter() - request._start_time
            endpoint = request.endpoint or "unknown"

            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)

            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
            ).inc()

        return response

    @app.route("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)