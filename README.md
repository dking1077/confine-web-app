# Overview

Confine is a Flask backend that takes a free-text music search, enriches it through external APIs and an LLM-based parser, and returns structured, cached results to authenticated users. It was built to explore production-style backend patterns — async task orchestration, caching, auth, and observability — in a project small enough to reason about end to end but real enough to deploy.

## What it does

A user submits a search (e.g. an artist, album, or lyric fragment). The request is validated, queued as a background job, and resolved through a layered lookup: cache first, then external APIs (MusixMatch for metadata, OpenRouter for AI-assisted parsing of ambiguous input), with results persisted for reuse. The user then works with results in a tabbed workspace, moving items through analysis and processing steps.

- Authenticated search with JWT access/refresh tokens
- Async processing via Celery, so slow third-party API calls never block a request
- Postgres-backed cache layer to avoid redundant external API calls
- Structured, consistent JSON responses across every endpoint
- Request correlation IDs that trace a single request across Flask and Celery
- Audit logging for security-relevant user actions

## Why these design choices

- **Celery + Redis, not synchronous calls** — MusixMatch and OpenRouter both have latency and rate limits I don't control. Making the search endpoint async means a slow or rate-limited upstream call never blocks the request thread, and retries/backoff can be handled centrally instead of per-caller.
- **Postgres cache before external calls** — repeated searches for the same artist/track are common; hitting the database first meaningfully cuts external API usage and latency on warm queries.
- **Centralized response contract (`ok` / `code` / `message` / `data`)** — every route returns the same shape whether it succeeds or fails, which makes the frontend's error handling and any future API consumer's integration trivial and predictable.
- **Request IDs propagated through Celery** — once work leaves the Flask process and enters a task queue, tracing a single user action across logs gets hard fast. Binding a request ID at the entrypoint and threading it through task signals keeps that traceable.

## Tech stack

**Backend:** Python, Flask (app factory + Blueprints), SQLAlchemy, Marshmallow, Celery, Alembic
**Infra:** PostgreSQL, Redis, Docker / docker-compose, Kubernetes manifests, Gunicorn
**External services:** MusixMatch API, OpenRouter (LLM parsing), Sentry (error monitoring)
**CI/CD:** GitHub Actions, pytest

## Architecture

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
├── routes.py           # HTML page routes
├── database.py         # Database bootstrap helpers
└── __init__.py          # App factory

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

### Request flow

1. A user authenticates through `/auth/register` or `/auth/login` and receives a JWT access/refresh pair.
2. Protected routes use the JWT identity to scope data to the current user.
3. A search is submitted to `/search/`, validated with Marshmallow, and dispatched as a Celery chain.
4. The chain checks the Postgres cache first, falls back to MusixMatch for raw data, and uses OpenRouter to parse ambiguous or unstructured input. Results are written to Redis-backed tab state.
5. Workspace actions under `/tabs/*` move results through analysis and processing steps.
6. Every response — success or failure — follows the same JSON contract, with request correlation data attached for tracing.

## API reference

All successful responses follow:

```json
{
  "ok": true,
  "code": "SEARCH_SUCCESS",
  "message": "Search completed successfully.",
  "data": {}
}
```

All error responses follow:

```json
{
  "ok": false,
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed.",
  "details": {}
}
```

| Area   | Endpoint                     | Description                     |
|--------|-------------------------------|----------------------------------|
| Auth   | `POST /auth/register`         | Create a new user                |
| Auth   | `POST /auth/login`            | Authenticate, issue JWT pair     |
| Auth   | `POST /auth/logout`           | Revoke current token             |
| Auth   | `GET /auth/session-status`    | Check current session validity   |
| Auth   | `POST /auth/refresh`          | Exchange refresh token for access token |
| Search | `POST /search/`               | Submit a search, dispatches Celery chain |
| Tabs   | `POST /tabs/add_to_panel`     | Add a result to the workspace    |
| Tabs   | `POST /tabs/remove_from_panel`| Remove a result from the workspace |
| Tabs   | `POST /tabs/analyze_items`    | Run analysis on workspace items  |
| Tabs   | `POST /tabs/process_items`    | Process workspace items          |

## Running locally

```bash
git clone https://github.com/dking1077/confine-web-app.git
cd confine-web-app
cp .env.example .env   # add your MusixMatch / OpenRouter keys
docker-compose up --build
```

This starts the Flask app, Celery worker, PostgreSQL, and Redis. Migrations run via Alembic:

```bash
alembic upgrade head
```

## Testing

```bash
pytest
```

Tests focus on the centralized API response contract holding across failure modes rather than just checking status codes in isolation:

- Unauthenticated requests to protected routes return a consistent `401` envelope
- Marshmallow validation failures return a consistent `400` envelope with error `details`
- Unknown routes return a consistent `404` envelope rather than Flask's default HTML error page

## Deployment

- `Dockerfile` builds a production image served with Gunicorn (`wsgi:app`)
- `docker-compose.prod.yml` defines a production-style multi-service layout
- `k8s/` contains Kubernetes manifests for the web service, Celery worker, Redis, PostgreSQL, config, and secrets
