FROM python:3.13-slim

WORKDIR /app

# Install system dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifest files first.
COPY pyproject.toml uv.lock* ./

# Install dependencies.
RUN uv sync --frozen --no-dev

# Copy the rest of the application code.
COPY . .

# Create directories used by mounted volumes.
RUN mkdir -p /app/instance /app/keys /app/logs

EXPOSE 5000

CMD ["uv", "run", "run.py"]