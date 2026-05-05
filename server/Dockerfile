FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifest files first.
COPY pyproject.toml uv.lock* ./

# Install dependencies.
RUN uv sync --frozen --no-dev

# Copy the rest of the application code.
COPY . .

RUN mkdir -p /app/instance /app/keys /app/logs

EXPOSE 5000

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "run:app"]