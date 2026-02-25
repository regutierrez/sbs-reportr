# Stage 1: Build the Vue frontend
FROM oven/bun:1 AS frontend
WORKDIR /app
COPY src/frontend/package.json src/frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY src/frontend/ .
RUN bun run build

# Stage 2: Install Python dependencies
FROM python:3.13-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src/reportr/ src/reportr/
RUN uv sync --frozen --no-dev

# Stage 3: Runtime
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    fontconfig \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY --from=builder /app/src src
# Logo SVGs referenced by the PDF renderer at src/frontend/public/
COPY src/frontend/public/asset-80.svg src/frontend/public/asset-79.svg src/frontend/public/
COPY --from=frontend /app/dist /app/frontend-dist
EXPOSE 9999
CMD ["sh", "-c", "cp -r /app/frontend-dist/* /srv/frontend/ && exec .venv/bin/uvicorn reportr.app.web_api:app --host 0.0.0.0 --port 9999"]
