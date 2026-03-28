FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY collected_company/ collected_company/
COPY scripts/ scripts/


FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --create-home app

# Copy virtual environment and app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/collected_company collected_company/
COPY --from=builder /app/scripts scripts/
COPY docker-entrypoint.py /app/docker-entrypoint.py

# Create data directory for SQLite (owned by app user)
RUN mkdir -p /app/data && chown -R app:app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV DATABASE_URL="sqlite+aiosqlite:///./data/collected_company.db"

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

ENTRYPOINT ["python", "/app/docker-entrypoint.py"]
