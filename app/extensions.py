from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import inspect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager
from celery import Celery
from app.errors import error_response
from app.models import Base
import logging
import os
import redis

logger = logging.getLogger(__name__)

celery = Celery(__name__)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/1")
)

# redis dbs: 0 celery, 1 limiter, 2 search cache, 3 token blocklist, 4 job owners
redis_blocklist = redis.Redis.from_url(
    os.getenv("REDIS_URL_BLOCKLIST", "redis://redis:6379/3"),
    decode_responses=True
)
redis_jobs = redis.Redis.from_url(
    os.getenv("REDIS_URL_JOBS", "redis://redis:6379/4"),
    decode_responses=True
)

engine = None
db_session = None
jwt = JWTManager()

def init_db(config):
    global engine, db_session
    db_uri = f'postgresql://{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}'
    engine = create_engine(db_uri, pool_pre_ping=True)
    session = sessionmaker(bind=engine, autoflush=False)
    db_session = scoped_session(session)

    query = text('SELECT version();')
    result = db_session.execute(query)

    db_version = result.fetchone()[0]
    logger.info("connected to PostgreSQL! Server version: %s", db_version)


def create_tables():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    expected_tables = Base.metadata.tables.keys()

    missing_tables = [table for table in expected_tables if table not in existing_tables]

    if missing_tables:
        Base.metadata.create_all(engine)


def init_celery(app):
    celery.conf.update(
        broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        task_track_started=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        worker_hijack_root_logger=False,
        worker_redirect_stdouts=True,
        worker_redirect_stdouts_level="INFO",
        worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
        result_expires=3600
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask


def init_jwt(app):
    jwt.init_app(app)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return error_response(
            code="AUTH_TOKEN_EXPIRED",
            message="The access token has expired.",
            status_code=401,
            details={"logged_in": False},
        )

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return error_response(
            code="AUTH_TOKEN_INVALID",
            message="The access token is invalid.",
            status_code=401,
            details={"logged_in": False},
        )

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return error_response(
            code="AUTH_TOKEN_REVOKED",
            message="The token has been revoked.",
            status_code=401,
            details={"logged_in": False},
        )

    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return error_response(
            code="AUTH_UNAUTHORIZED",
            message="Authentication is required.",
            status_code=401,
            details={"logged_in": False},
        )