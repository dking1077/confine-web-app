from flask import Blueprint, render_template, jsonify
from sqlalchemy import text
from app import extensions
import logging


logger = logging.getLogger(__name__)
bp = Blueprint("app", __name__)


# index root
@bp.route("/")
def index():
    return render_template("index.html")


# session root
@bp.route("/session")
def session_pg():
    return render_template("session.html")


# health check - verifies the database, not just the process
@bp.route("/health")
def health():
    try:
        extensions.db_session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception:
        logger.exception("health check failed")
        return jsonify({"status": "error", "db": "disconnected"}), 503


@bp.route("/sentry-test")
def sentry_test():
    raise Exception("Sentry test error")