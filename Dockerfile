# syntax=docker/dockerfile:1

# --- Base image -------------------------------------------------------------
FROM python:3.12-slim AS base

# Keep Python lean and predictable in containers.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# Copy everything the build backend needs BEFORE installing. The package
# metadata (pyproject.toml) references README.md and discovers the ``app``
# package, so both must be present at install time.
COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

RUN pip install --upgrade pip && pip install .

# Run as a non-root user (security best practice).
RUN useradd --create-home appuser && chown -R appuser:appuser /code
USER appuser

EXPOSE 8000

# The entrypoint applies migrations, then starts the server.
CMD ["sh", "scripts/entrypoint.sh"]
