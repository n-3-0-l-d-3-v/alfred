# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Requirements first so the dependency layer survives source-only changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY migrations/ ./migrations/
COPY leetlearn/ ./leetlearn/

# Non-root: nothing here needs to write outside the image.
RUN useradd --create-home --uid 10001 leetlearn
USER leetlearn

EXPOSE 8000

# Migrations run at boot so a deploy can never serve a schema older than its
# code. `upgrade head` is a no-op when the database is already current.
CMD ["sh", "-c", "alembic upgrade head && uvicorn leetlearn.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
