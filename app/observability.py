from flask import g, request
import logging
import uuid


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

    @app.after_request
    def attach_request_id(response):
        response.headers["X-Request-ID"] = get_request_id()
        return response