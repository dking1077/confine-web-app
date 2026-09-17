from flask import Flask
from flask_cors import CORS
from .database import db_create
from app.routes import bp as main_bp
from app.auth.routes import bp as auth_bp
from app.search.routes import bp as search_bp
from app.tabs.routes import bp as tabs_bp
from app.logger import configure_logging
from app.models import Base
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from app.errors import ApiError, error_response
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
import sentry_sdk
from . import extensions
import logging


def create_app(config=None):
    """
    creates the flask application
    configures the local postgres database
    configures a scoped db session to be used - one per request
    closes each session automatically when the request ends
    first SQL execution within request - connection opened - taken from pool
    end of request - flask teardown calls session remove - connection closed returned to the pool
    :param config:
        the applications run configurations defined in config.py
    database.py is used here so need to import the module, in services we can import the variables
    """
    # configure logging
    configure_logging()

    # start logs
    logger = logging.getLogger(__name__)
    logger.info('\napplication starting ..')

    # flask instance
    app = Flask(__name__)
    if config:
        app.config.from_object(config)

    # init sentry
    sentry_dsn = app.config.get("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=app.config.get("SENTRY_ENVIRONMENT", "development"),
            traces_sample_rate=float(app.config.get("SENTRY_TRACES_SAMPLE_RATE", 0.0)),
            integrations=[
                FlaskIntegration(),
                CeleryIntegration(),
            ],
        )

    # create database
    db_create(config)

    # init database
    extensions.init_db(config)

    # create tables
    Base.metadata.create_all(extensions.engine)

    # register routes.py
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(tabs_bp)

    # init celery
    extensions.init_celery(app)

    # init rate limiting
    extensions.limiter.init_app(app)

    # init jwt
    extensions.init_jwt(app)

    # error handlers
    @app.errorhandler(ApiError)
    def handle_api_error(err):
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
            message="Request validation failed",
            status_code=400,
            details=err.messages,
        )

    @app.errorhandler(404)
    def handle_404(err):
        return error_response(
            code="NOT_FOUND",
            message="The requested URL was not found on the server.",
            status_code=404,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return error_response(
            code=err.name.upper().replace(" ", "_"),
            message=err.description,
            status_code=err.code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        logger.exception("Unhandled exception: %s", err)
        return error_response(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            status_code=500,
        )

    # allow browser headers across ports!
    CORS(app, resources={r"/*": {"origins": "*"}},
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

    # remove session after request
    @app.teardown_appcontext
    def remove_session(exception=None):
        extensions.db_session.remove()

    return app