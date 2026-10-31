# Space Bounty Hunters API

Midterm practical assignment (Web Development, KBTU). REST API for space bounty hunters:
a database of wanted criminals and a journal of bounty-hunting attempts.

**Stack:** FastAPI, SQLAlchemy (async), Alembic, PostgreSQL 16, Docker Compose.

## Run

```bash
docker compose up -d --build
```

- API: http://localhost:8000/api
- Swagger UI: http://localhost:8000/api/docs

On startup the backend container:
1. applies Alembic migrations (`alembic upgrade head`) — creates `wanted_criminals` and `hunt_logs`;
2. prefills the database (if empty) with **6 criminals** and **11 hunt logs** ([app/seed.py](app/seed.py)).

Reset the database: `docker compose down -v && docker compose up -d --build`.

### Without Docker

Requires a running PostgreSQL and [uv](https://docs.astral.sh/uv/).

```bash
export POSTGRES_HOST=localhost POSTGRES_USER=bounty POSTGRES_PASSWORD=bounty POSTGRES_DB=bounty
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --port 8000
```

## Models

**WantedCriminal** (`wanted_criminals`)

| Field | Type | Notes |
|---|---|---|
| id | int | PK |
| name | string, nullable | real name, may be unknown |
| nickname | string | alias |
| reward | decimal | `>= 0` |
| latitude, longitude | float, nullable | last known coordinates |
| location_note | text, nullable | last known location as a text note |
| difficulty | int | 1–10 |
| armed, has_crew, escape_master | bool | |

**HuntLog** (`hunt_logs`)

| Field | Type | Notes |
|---|---|---|
| id | int | PK |
| criminal_id | int | FK → `wanted_criminals.id` (ON DELETE CASCADE) |
| success | bool | |
| notes | text | |
| created_at | timestamptz | set by the server (`DEFAULT now()`) |

Relationship: one `WantedCriminal` → many `HuntLog`.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/criminals/` | List criminals. Query: `min_reward`, `max_reward`, `armed`, `has_crew`, `escape_master`, `sort` (`reward` / `-reward`). Filters combine. |
| GET | `/api/criminals/{id}/` | Criminal details (incl. hunt logs) |
| GET | `/api/hunts/` | List hunt logs. Query: `criminal_id` |
| GET | `/api/hunts/{id}/` | Get one hunt log |
| POST | `/api/hunts/` | Create hunt log |
| PATCH | `/api/hunts/{id}/` | Update `success` and/or `notes` |
| DELETE | `/api/hunts/{id}/` | Delete hunt log |

Example: `GET /api/criminals/?min_reward=5000&armed=true&sort=-reward`

POST body:

```json
{ "criminal_id": 3, "success": false, "notes": "Target escaped through an asteroid field." }
```

### Status codes

| Code | When |
|---|---|
| 200 | OK |
| 201 | Hunt log created |
| 204 | Hunt log deleted |
| 400 | `criminal_id` references a non-existent criminal; empty PATCH; `min_reward > max_reward` |
| 404 | Criminal / hunt log not found |
| 422 | Invalid body or params (missing fields, wrong types, unknown fields such as `created_at`, invalid `sort`, non-integer id) |

## Postman

Import [postman/BountyHunters.postman_collection.json](postman/BountyHunters.postman_collection.json)
(variable `baseUrl` = `http://localhost:8000/api`). It covers listing, filtering, sorting,
details, hunt log CRUD and invalid requests, each with tests.

Run from CLI:

```bash
npx -y newman run postman/BountyHunters.postman_collection.json
```
