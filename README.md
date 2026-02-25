# SBS Reportr

SBS Reportr is a report-building app for structural activity documentation.
It combines a FastAPI backend (session + image upload + PDF generation) with a Vue 3 frontend intake form.

## Tech Stack

- Backend: Python 3.13+, FastAPI, Pydantic, Pillow, WeasyPrint
- Frontend: Vue 3, Vite, TypeScript
- Tooling: `uv` (Python), `bun` (frontend/scripts)

## Repository Layout

- `src/reportr/` - backend API, storage, and PDF rendering
- `src/frontend/` - Vue app for report intake and confirmation
- `tests/` - backend API tests
- `docs/reference/` - canonical reference assets for report template parity
- `data/` - runtime session/report storage (created at runtime)

## Prerequisites

- Python `3.13+`
- `uv`
- `bun`

## Local Setup

1. Install backend dependencies:

```bash
uv sync --dev
```

2. Install frontend dependencies:

```bash
bun install --cwd src/frontend
```

## Running Locally

### Backend API

```bash
PYTHONPATH=src uv run uvicorn reportr.app.web_api:app --reload --host 127.0.0.1 --port 9999
```

Health check:

```bash
curl http://127.0.0.1:9999/health
```

By default, runtime data is written under `data/` at the repository root.
You can override storage paths with environment variables:

- `REPORTR_DATA_ROOT` (base directory; defaults to `<repo>/data`)
- `REPORTR_SESSIONS_ROOT` (optional explicit sessions directory)
- `REPORTR_REPORTS_ROOT` (optional explicit reports directory)

Example:

```bash
REPORTR_DATA_ROOT=/tmp/reportr-data \
PYTHONPATH=src uv run uvicorn reportr.app.web_api:app --reload --host 127.0.0.1 --port 9999
```

### Frontend

```bash
VITE_API_BASE_URL=http://127.0.0.1:9999 bun run --cwd src/frontend dev
```

## Docker storage configuration

`docker-compose.yml` and `example-docker-compose.yml` set:

- `REPORTR_DATA_ROOT=/tmp/reportr` inside the container
- a persistent Docker volume mounted to that same path

To change it, update `REPORTR_DATA_ROOT` in the compose file and keep the volume mount destination in sync.

## Validation

- Backend changes:

```bash
uv run ruff format . && uv run basedpyright && uv run pytest
```

- Frontend changes:

```bash
bun run --cwd src/frontend lint && bun run --cwd src/frontend build
```

## Useful Root Scripts

From the repository root:

- `bun run lint` - lint backend + frontend
- `bun run typecheck` - type check backend + frontend
- `bun run test` - run backend + frontend unit tests
- `bun run build` - build frontend
- `bun run check` - lint + typecheck + build + tests

## API Workflow (High Level)

1. `POST /reports` to create a draft session.
2. `PUT /reports/{session_id}` to save form fields.
3. `POST /reports/{session_id}/images/{group_name}` to upload required images.
4. `POST /reports/{session_id}/generate` to render and persist PDF output.
5. `GET /reports/{session_id}/download` to download the generated report.

## Runtime Limits (Enforced by API)

- Allowed image MIME types: `image/jpeg`, `image/png`, `image/webp`
- Max single image size: `15 MB`
- Max total upload size per session: `300 MB`
- Max image longest side: `1200 px`
