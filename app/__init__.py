from flask import Flask
from flask_cors import CORS
from .database import db_create
from app.routes import bp as main_bp
from app.auth.routes import bp as auth_bp
from app.search.routes import bp as search_bp
from app.tabs.routes import bp as tabs_bp
from app.logger import configure_logging
from app.errors import register_error_handlers
from app.observability import init_observability
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
import sentry_sdk
from . import extensions
import logging


def create_app(config=None, is_worker=False):
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
    logger.info('\napplication starting ..', extra={"request_id": "-"})

    # flask instance
    app = Flask(__name__)
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    if config:
        app.config.from_object(config)

    # init observability
    init_observability(app)

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

    # create database & initialize connections
    if not is_worker:
        db_create(config)
        extensions.init_db(config)
        extensions.create_tables()
    else:
        extensions.init_db(config)

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

    # centralized api errors
    register_error_handlers(app)

    # allow browser headers across ports!
    CORS(
        app,
        resources={r"/auth/*": {"origins": "*"}, r"/search/*": {"origins": "*"}, r"/tabs/*": {"origins": "*"}},
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        return response

    # remove session after request
    @app.teardown_appcontext
    def remove_session(exception=None):
        extensions.db_session.remove()

    return app