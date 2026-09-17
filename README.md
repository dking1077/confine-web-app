# Confine Web App

Confine is a Flask-based web application that processes music-related search input, enriches it with external APIs and AI parsing, and serves structured results to authenticated users.

## What this project does
- Accepts authenticated search requests
- Parses and processes user input through async backend workflows
- Stores and retrieves relational data for artists, albums, tracks, users, and search results
- Returns structured tabbed results for client consumption

## Engineering Concepts
- Flask app factory pattern and modular Blueprints
- RESTful route design with JSON request/response handling
- JWT authentication (access/refresh flow and token revocation)
- Request rate limiting for auth and search endpoints
- SQLAlchemy ORM modeling with relationships and uniqueness constraints
- Scoped database sessions and PostgreSQL integration
- Background task orchestration with Celery chains
- Redis-backed infrastructure for Celery broker/result and rate-limit storage
- Input validation and schema enforcement with Marshmallow
- External service integration patterns (MusixMatch and OpenRouter)
- Structured logging and Sentry-based error monitoring
- Database migration scaffolding with Alembic

## Project structure
```
app/
├── auth/          # Registration, login, logout, token refresh
├── cache/         # Cache lookup and result storage logic
├── celery/        # Task definitions, worker config, and signals
├── logic/         # Search and cache pipeline orchestration
├── models.py      # SQLAlchemy ORM models
├── schemas.py     # Marshmallow validation schemas
├── extensions.py  # Shared extensions (db, celery, jwt, limiter)
├── logger.py      # Logging configuration
├── prompts.py     # AI prompt templates
├── search/        # Search routes and database queries
├── services/      # MusixMatch and OpenRouter API clients
├── tabs/          # Tab result building and transformation routes
├── database.py    # DB creation and table initialisation
└── __init__.py    # App factory

alembic/           # Database migration scripts
tests/             # Pytest test suite
```

