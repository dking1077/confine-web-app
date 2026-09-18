# Overview

Confine is a Flask-based web application that processes music-related search input, enriches it with external APIs and AI parsing, and serves structured results to authenticated users.

## What this project does
- Accepts authenticated search requests
- Parses and processes user input through async backend workflows
- Stores and retrieves relational data for artists, albums, tracks, users, and search results
- Returns structured tabbed results for client consumption
- Tracks request flow with centralized API responses, audit-style logs, and request IDs
- Supports local Docker development and production-style Gunicorn startup

## Engineering concepts
- Flask app factory pattern and modular Blueprints
- RESTful route design with JSON request/response handling
- JWT authentication (access/refresh flow and token revocation)
- Request rate limiting for auth and search endpoints
- SQLAlchemy ORM modeling with relationships and uniqueness constraints
- Scoped database sessions and PostgreSQL integration
- Background task orchestration with Celery chains
- Redis-backed infrastructure for Celery broker/result and rate-limit storage
- Input validation and schema enforcement with Marshmallow
- Centralized success/error response contracts for API routes
- Audit logging for critical user actions
- Request correlation with request IDs across Flask and Celery
- External service integration patterns (MusixMatch and OpenRouter)
- External API retry/timeout handling
- Structured logging and Sentry-based error monitoring
- Database migration scaffolding with Alembic
- GitHub Actions CI support for automated tests

## Structure
```text
app/
├── auth/              # Registration, login, logout, session status, token refresh
├── cache/             # Cache lookup and result storage logic
├── celery/            # Task definitions, worker config, and signals
├── logic/             # Search and cache pipeline orchestration
├── services/          # MusixMatch and OpenRouter API clients
├── search/            # Search routes and database queries
├── tabs/              # Tab result building and transformation routes
├── static/            # Frontend JavaScript for auth, session, and index flows
├── audit.py           # Audit logging helper
├── errors.py          # Centralized API success/error response helpers and handlers
├── observability.py   # Request ID binding and propagation helpers
├── models.py          # SQLAlchemy ORM models
├── schemas.py         # Marshmallow validation schemas and AI response validators
├── extensions.py      # Shared extensions (db, celery, jwt, limiter)
├── logger.py          # Logging configuration
├── prompts.py         # AI prompt templates
├── routes.py          # HTML page routes
├── database.py        # Database bootstrap helpers
└── __init__.py        # App factory

alembic/                # Database migration scripts
.github/workflows/      # GitHub Actions CI
k8s/                    # Kubernetes manifests
tests/                  # Pytest test suite
Dockerfile              # Container image definition
docker-compose.yml      # Local development services
docker-compose.prod.yml # Production-style compose services
run.py                  # Development entrypoint
wsgi.py                 # Production WSGI entrypoint
```

## Runtime flow
1. A user authenticates through `/auth/register` or `/auth/login`.
2. Protected API routes use JWT identity to scope requests to the current user.
3. Search input is submitted to `/search/`, validated with Marshmallow, and dispatched through a Celery chain.
4. Search parsing uses OpenRouter, search retrieval uses PostgreSQL cache/lookup plus MusixMatch fallback, and results are written into Redis-backed tab state.
5. Workspace actions in `/tabs/*` move search results through workspace, concept, semantic, and process flows.
6. Responses return a consistent JSON contract with `ok`, `code`, `message`, and `data`.
7. Logging, audit events, and request IDs help trace a request across Flask and Celery.

## API response contract
Successful API responses follow this shape:

```json
{
  "ok": true,
  "code": "SEARCH_SUCCESS",
  "message": "Search completed successfully.",
  "data": {}
}
```

Error responses follow this shape:

```json
{
  "ok": false,
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed.",
  "details": {}
}
```

Most API responses also include request correlation information for tracing.

## Main API areas
### Auth
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/session-status`
- `POST /auth/refresh`

### Search
- `POST /search/`

### Tabs / workflow
- `POST /tabs/add_to_panel`
- `POST /tabs/remove_from_panel`
- `POST /tabs/analyze_items`
- `POST /tabs/process_items`

## Deployment notes
- `Dockerfile` uses Gunicorn with `wsgi:app`
- `docker-compose.prod.yml` provides a production-style multi-service layout
- `k8s/` contains Kubernetes manifests for web, worker, Redis, Postgres, config, and secrets

