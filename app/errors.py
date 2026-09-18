from flask import jsonify, request
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException
from app.observability import get_request_id
import logging


logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, code, message, status_code=400, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def success_response(code="SUCCESS", message="OK", data=None, status_code=200):
    return jsonify({
        "ok": True,
        "code": code,
        "message": message,
        "data": {} if data is None else data,
        "request_id": get_request_id(),
    }), status_code


def error_response(code, message, status_code=400, details=None):
    response_details = details or {}
    response_details["request_id"] = get_request_id()
    return jsonify({
        "ok": False,
        "code": code,
        "message": message,
        "details": response_details,
    }), status_code


def is_api_request():
    if request.path.startswith("/auth"):
        return True
    if request.path.startswith("/search"):
        return True
    if request.path.startswith("/tabs"):
        return True
    return False


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        logger.warning(
            "api error: code=%s message=%s",
            err.code,
            err.message,
            extra={"request_id": get_request_id()},
        )
        return error_response(
            code=err.code,
            message=err.message,
            status_code=err.status_code,
            details=err.details,
        )

    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            status_code=400,
            details=err.messages,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        if is_api_request():
            return error_response(
                code=f"HTTP_{err.code}",
                message=err.description,
                status_code=err.code,
                details={"path": request.path},
            )
        return err

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        logger.exception(
            "unhandled exception: %s",
            err,
            extra={"request_id": get_request_id()},
        )
        if is_api_request():
            return error_response(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred.",
                status_code=500,
                details={"path": request.path},
            )
        raise err