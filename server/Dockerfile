# ─── Stage 1: Build React frontend ───────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /client

COPY client/package.json client/package-lock.json* ./
RUN npm ci

COPY client/ ./
RUN npm run build

# ─── Stage 2: Python application ─────────────────────────────────────────────
FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY server/pyproject.toml server/uv.lock* ./

RUN uv sync --frozen --no-dev

COPY server/ .

# Copy built React static files from Stage 1
COPY --from=frontend-builder /server/app/static ./app/static/

RUN mkdir -p /app/keys /app/logs

EXPOSE 5000

CMD ["uv", "run", "gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--worker-class", "gevent", \
     "--workers", "1", \
     "--worker-connections", "100", \
     "--timeout", "120", \
     "run:app"]