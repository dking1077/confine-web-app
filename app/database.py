from sqlalchemy import create_engine, text
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
        else:
            logger.info(f"super user '{config.DB_USER}' already exists.")

        # create database
        db_exists = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname='{config.DB_NAME}'")
        ).fetchone()
        if not db_exists:
            sql = text(f"""CREATE DATABASE {config.DB_NAME}
                           WITH
                           OWNER = {config.DB_USER}
                           CONNECTION LIMIT = -1; """)
            conn.execute(sql)
            logger.info(f"database '{config.DB_NAME}' created successfully!")
        else:
            logger.info(f"database '{config.DB_NAME}' already exists.")