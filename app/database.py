from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from .models import Base
import logging


logger = logging.getLogger(__name__)


def db_create(config):
    default_engine = create_engine(
        f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASS}@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/postgres", isolation_level="AUTOCOMMIT")

    with default_engine.connect() as conn:
        # create superuser role
        role_exists = conn.execute(
            text(f"SELECT 1 FROM pg_roles WHERE rolname = '{config.DB_USER}'"),
        ).fetchone()
        if not role_exists:
            try:
                sql = text(f"""CREATE ROLE {config.DB_USER} WITH
                               LOGIN
                               SUPERUSER
                               CREATEDB
                               CREATEROLE
                               INHERIT
                               REPLICATION
                               BYPASSRLS
                               CONNECTION LIMIT -1
                               PASSWORD '{config.DB_PASS}';""")
                conn.execute(sql)
                logger.info(f"super user '{config.DB_USER}' created successfully!")
            except (ProgrammingError, OperationalError) as e:
                if "already exists" in str(e):
                    logger.info(f"super user '{config.DB_USER}' already exists.")
                else:
                    raise e
        else:
            logger.info(f"super user '{config.DB_USER}' already exists.")

        # create database
        db_exists = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname='{config.DB_NAME}'")
        ).fetchone()
        if not db_exists:
            try:
                sql = text(f"""CREATE DATABASE {config.DB_NAME}
                               WITH
                               OWNER = {config.DB_USER}
                               CONNECTION LIMIT = -1; """)
                conn.execute(sql)
                logger.info(f"database '{config.DB_NAME}' created successfully!")
            except (ProgrammingError, OperationalError) as e:
                if "already exists" in str(e):
                    logger.info(f"database '{config.DB_NAME}' already exists.")
                else:
                    raise e
        else:
            logger.info(f"database '{config.DB_NAME}' already exists.")


def create_tables(engine):
    Base.metadata.create_all(engine)