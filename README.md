# MkJobs-API

MkJobs API is a tool that aggregates publicly listed job postings from Macedonian employment portals, company career pages, and government job boards into a single, queryable dataset.

It provides:
- A unified REST API over job postings collected from multiple independent sources
- Scheduled scraping agents with per-source rate limiting and retry policies
- Deduplication and normalization of postings that appear across multiple portals
- Asynchronous task processing for scraping, enrichment, and notification fanout

The stack is built around **FastAPI**, **SQLAlchemy**, **PostgreSQL**, **Celery**, and **Redis**.

> This repository was built as an academic project demonstrating a production-shaped
> data aggregation service: async API layer, background workers, cron-style
> scheduling, cursor pagination, and event-driven webhook notifications.
> Two example source adapters (`vrabotuvanje`, `cv_mk`) are included as scraper
> *templates* — their CSS selectors / JSON field names are illustrative
> placeholders and should be adapted to the real markup of each target site,
> and each site's robots.txt / terms of service should be reviewed before
> enabling scraping against it in production.

## Quick Start

Run with Docker (recommended):

```bash
# 1. Create local environment and secret files
cp .env.example .env
mkdir -p secrets
openssl rand -base64 32 > secrets/postgres_password.txt

# 2. Ensure the reverse-proxy Docker network exists
docker network create edge-proxy || true

# 3. Start Postgres and Redis, run migrations once, then start the stack
docker compose up -d postgres redis
docker compose --profile tools run --rm migrate
docker compose up -d api worker beat

# 4. Verify service readiness from inside the api container
docker compose exec api curl -s http://localhost:8000/api/ping
docker compose exec api curl -s http://localhost:8000/api/ready
```

Run locally (development):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# optional: seed a few sample postings without running the scrapers
python -m scripts.seed
```

## Key Features

| Feature | Description |
|---|---|
| Multi-source scraping | Pluggable scraper strategies per job portal, with isolated failure handling |
| Deduplication engine | Fuzzy-matches postings across sources by title, employer, and location (RapidFuzz) |
| Contract APIs | Cursor-based GET endpoints for job postings, employers, and categories |
| Input validation | Pydantic models with strict typing on all request/response payloads |
| Production-safe middleware | CORS, request IDs, rate limiting, and centralized error handling |
| Beat scheduler | Periodic scraping runs via Celery Beat with configurable intervals per source |
| Notification fanout | Webhook delivery when new postings match saved filters |
| Structured logging | JSON logging via structlog, shipped to stdout for container log collection |

## Architecture

```
Shared Core
  -> core/        (settings, db session, logging, security)
  -> common/      (schemas, enums, pagination helpers)
  -> sources/     (per-portal scraper strategies, parsers, normalizers)

Execution Surfaces
  -> API process        (request/response, FastAPI + Uvicorn)
  -> Celery worker       (scraping tasks, enrichment, notification dispatch)
  -> Celery beat         (cron-style scheduling of scraping runs)

Celery Worker
  -> Scraping tasks (per source)
  -> Deduplication + normalization pipeline
  -> Notification dispatcher

Celery Beat
  -> Triggers scraping tasks on a per-source schedule
```

### Runtime processes

| Process | Entry point | Purpose |
|---|---|---|
| API | `app/main.py` | Serves `/api` endpoints |
| Worker | `app/worker.py` | Executes scraping, enrichment, and notification tasks |
| Beat | Celery Beat (same image, different command) | Triggers scheduled scraping runs |

## Project Structure

```
app/
  main.py
  worker.py
  core/
    config.py
    db.py
    logging.py
    security.py
  sources/
    registry.py
    base.py
    vrabotuvanje/
      scraper.py
      parser.py
      schedule.py
    cv_mk/
      scraper.py
      parser.py
      schedule.py
  api/
    routes/
    dependencies.py
  common/
    schemas/
    pagination.py
    enums.py
  models/
  tasks/
    scraping.py
    dedup.py
    notifications.py
  webhooks/
    dispatch.py
alembic/
  versions/
scripts/
  seed.py
```

| Path | Responsibility |
|---|---|
| `app/core` | App bootstrap, DB session factory, logging config, request/rate-limit helpers |
| `app/sources` | One module per job portal: scraping logic, HTML/JSON parsing, cron schedule |
| `app/api/routes` | Route handlers, request validation, response serialization |
| `app/common` | Cross-cutting schemas, pagination utilities, shared enums |
| `app/tasks` | Celery tasks: scraping orchestration, dedup, notification fanout |
| `app/webhooks` | Webhook URL collection (by env prefix) and delivery |
| `alembic` | Database migration history |

## Run Modes

### Prerequisites
- Python 3.12+
- PostgreSQL 16
- Redis 7
- Docker and Docker Compose (recommended for production-like runs)

### Development Mode

```bash
pip install -r requirements.txt
cp .env.example .env
```

Set required values:
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mkjobs
REDIS_URL=redis://localhost:6379/0
PORT=8000
```

Run migrations:
```bash
alembic upgrade head
```

Start each process in a separate terminal:
```bash
uvicorn app.main:app --reload --port 8000
celery -A app.worker worker --loglevel=info
celery -A app.worker beat --loglevel=info
```

If you only want the API without live scraping, skip the worker and beat processes.

### Production Mode (containerized)

In production, services run as containers using prebuilt images. The `docker-compose.yml`
here also includes a `build:` fallback so you can build locally instead of pulling from
a registry — update the `image:` fields to your own GHCR/Docker Hub path once you push one.

The api, worker, and beat containers construct `DATABASE_URL` internally from `POSTGRES_USER`, `POSTGRES_DB`, and the Docker secret mounted at `/run/secrets/postgres_password`. The API is expected to be reached through a reverse proxy or tunnel on the external `edge-proxy` network — no host port is published for the API container.

Before starting services, ensure the external reverse-proxy network exists:
```bash
docker network create edge-proxy || true
```

Run database, cache, and migrations first:
```bash
docker compose up -d postgres redis
docker compose --profile tools run --rm migrate
```

Run API + worker + beat:
```bash
docker compose up -d api worker beat
```

Check running services:
```bash
docker compose ps
```

## Usage

**Health checks**
```bash
curl http://localhost:8000/api/ping
curl http://localhost:8000/api/ready
```

**Discover endpoints**
```bash
curl http://localhost:8000/api/.well-known
```

**Fetch active job postings (paged)**
```bash
curl "http://localhost:8000/api/postings?pageSize=10"
```

**Fetch postings for a specific employer**
```bash
curl "http://localhost:8000/api/employers/1/postings?pageSize=10"
```

**Fetch next page using returned cursor**
```bash
curl "http://localhost:8000/api/postings?pageSize=10&cursor=<nextCursor-from-previous-response>"
```

**Fetch postings sorted by posted date**
```bash
curl "http://localhost:8000/api/postings?pageSize=10&sortBy=postedAt&sortDirection=desc"
```

**Trigger a scrape manually (from the worker container)**
```bash
docker compose exec worker python -c "from app.tasks.scraping import scrape_source; scrape_source.delay('vrabotuvanje')"
```

## API

Base URL: `/api`

### Core endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/ping` | Liveness check |
| GET | `/api/ready` | Readiness check (verifies DB and Redis connectivity) |
| GET | `/api/.well-known` | Endpoint discovery payload |
| GET | `/api/reference` | Reference dictionaries for categories, seniority levels, employment types |
| GET | `/api/stats` | Overview counts for postings, employers, and sources |

### Postings endpoints

| Method | Endpoint |
|---|---|
| GET | `/api/postings` |
| GET | `/api/postings/:id` |
| GET | `/api/postings/:id/history` |
| GET | `/api/employers` |
| GET | `/api/employers/:id` |
| GET | `/api/employers/:id/postings` |
| GET | `/api/categories` |
| GET | `/api/categories/:id/postings` |

### Pagination

All list endpoints support cursor pagination:

| Query param | Type | Default | Notes |
|---|---|---|---|
| `cursor` | string | none | Opaque cursor returned by previous response `meta.nextCursor` |
| `pageSize` | number | 10 | Min 1, max 100 |

Sortable cursor pagination is available on selected endpoints:

| Endpoint | Default sort | Supported `sortBy` values | `sortDirection` |
|---|---|---|---|
| `/api/postings` | `postedAt` | `postedAt`, `closingAt`, `salaryEstimate` | `asc`, `desc` |
| `/api/employers` | `id` | `id`, `activePostingsCount`, `totalPostingsCount` | `asc`, `desc` |
| `/api/postings/:id/history` | `changedAt` | `changedAt` | `asc`, `desc` |

Response envelope:

```json
{
  "data": [],
  "meta": {
    "nextCursor": "eyJzb3J0QnkiOiJwb3N0ZWRBdCIsInNvcnREaXJlY3Rpb24iOiJkZXNjIiwidmFsdWUiOiIyMDI2LTA2LTE1VDA5OjAwOjAwLjAwMFoiLCJpZCI6NDJ9",
    "pageSize": 10,
    "hasMore": true
  }
}
```

Notes:
- Treat `nextCursor` as an opaque token and pass it back exactly as received.
- If `cursor` is invalid or does not match current sort parameters, the API responds with HTTP 400 and message `Invalid cursor`.

### Filtering

`/api/postings` supports typed query filters in addition to pagination: `category` (slug), `seniority`, `employmentType`, `location` (substring match), `isActive`. Use `/api/reference` to resolve supported enum values.

## Environment Variables

| Variable | Required (Local Dev) | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string used for local development |
| `REDIS_URL` | Yes | Redis connection string used for Celery broker/backend |
| `PORT` | No | API port (defaults to 8000) |
| `NEW_POSTINGS_WEBHOOK_X` | No | Webhook URLs notified when new postings are found |
| `CLOSED_POSTINGS_WEBHOOK_X` | No | Webhook URLs notified when tracked postings are closed or removed |
| `POSTING_CHANGED_WEBHOOK_X` | No | Webhook URLs notified when a tracked posting's details change |

`.env` vs secrets. The `.env` file is used for non-secret runtime settings and local development (including `DATABASE_URL` when running outside containers). In Docker Compose deployment, the database password is read from the Docker secret mounted at `/run/secrets/postgres_password` and is not placed in `.env`. API and worker containers construct the full `DATABASE_URL` at startup from `POSTGRES_USER`, `POSTGRES_DB`, and the secret value.

Webhook variables are collected by prefix. You can register multiple endpoints by numbering with a trailing `_X` pattern (for example `_1`, `_2`, `_3`, ..., `_n`).

```
NEW_POSTINGS_WEBHOOK_1="https://example.com/hooks/new-postings-a"
NEW_POSTINGS_WEBHOOK_2="https://example.com/hooks/new-postings-b"
```

If no variables with a given prefix are present, dispatch is skipped for that event.

Webhook payload shape:

```json
{
  "data": [],
  "meta": {
    "event": "posting.new",
    "dispatchedAt": "2026-07-02T12:00:00.000Z"
  }
}
```

## Academic Notes

This project was implemented for coursework to demonstrate:
- Async web API design with FastAPI + SQLAlchemy 2.0 (async ORM)
- Keyset (cursor) pagination instead of offset pagination, including opaque
  token encoding/decoding and validation
- A background job system (Celery worker + beat) decoupled from the API process
- A basic text-similarity based deduplication pipeline (RapidFuzz token-set ratio)
- Event-driven integration via outbound webhooks, configured purely through
  environment variables
- Twelve-factor-style configuration (`.env` for non-secrets, Docker secrets
  for credentials) and a containerized, multi-service deployment topology

The two included source adapters are templates for demonstration purposes; no
scraping traffic is sent anywhere unless a Celery beat/worker process is
actually running and a task is triggered.

## License

This project is licensed under the MIT License.
