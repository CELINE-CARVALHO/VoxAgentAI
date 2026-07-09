# VoxAgent AI — Backend (FastAPI)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl is needed for the container HEALTHCHECK below.
# build-essential is needed to build a couple of the C-extension deps
# (e.g. bcrypt) on slim images; removed again after install to keep the
# image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y

COPY . .

# Runs as a non-root user in production.
RUN useradd --create-home --uid 1000 voxagent \
    && mkdir -p /app/uploads /app/db \
    && chown -R voxagent:voxagent /app
USER voxagent

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

# Single-process by default; scale replicas at the orchestrator level
# rather than via multiple uvicorn workers, since SQLite (the default
# DATABASE_URL) does not support concurrent writers well. Switch
# DATABASE_URL to Postgres before adding --workers > 1.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
