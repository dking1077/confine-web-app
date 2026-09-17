from flask import jsonify


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
        "data": data or {},
    }), status_code


def error_response(code, message, status_code=400, details=None):
    return jsonify({
        "ok": False,
        "code": code,
        "message": message,
        "details": details or {},
    }), status_code