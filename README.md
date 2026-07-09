# VoxAgent AI

A multilingual, retrieval-augmented AI voice call agent platform: FastAPI + SQLAlchemy backend, Groq LLM, and a vanilla HTML/CSS/JS frontend (no framework/build step).

## Run with Docker (recommended)

Requires Docker and Docker Compose.

```bash
cp backend/.env.example backend/.env
# then edit backend/.env and set GROQ_API_KEY and JWT_SECRET

docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000 (docs at http://localhost:8000/docs)
- Health check: http://localhost:8000/api/health

The SQLite database is stored on a named Docker volume (`voxagent-db`) so data survives `docker compose down` / rebuilds. To reset it entirely: `docker compose down -v`.

To stop: `docker compose down`. To rebuild after changing dependencies: `docker compose up --build`.

## Run locally (without Docker)

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env: set GROQ_API_KEY, JWT_SECRET
uvicorn main:app --reload --port 8000
```

**Frontend** — any static file server works, e.g.:
```bash
cd frontend
python3 -m http.server 5500
```
Open http://localhost:5500. If you serve the frontend on a different port, add that origin to `CORS_ORIGINS` in `backend/.env`.

## Database migrations

Dev convenience: the backend auto-creates tables on startup via `init_db()`. For an existing database with real data, use Alembic instead:
```bash
cd backend
alembic upgrade head
```

## Project structure

```
backend/
  app/
    routers/    # FastAPI route handlers
    models/     # SQLAlchemy models
    schemas/    # Pydantic request/response schemas
    crud/       # DB access functions
    services/   # Groq LLM, RAG, file extraction, security
  alembic/      # DB migrations
  main.py       # FastAPI app entrypoint
frontend/
  *.html        # One page per route (no SPA framework)
  css/
  js/
docker-compose.yml
```

## Environment variables

See `backend/.env.example` for the full list (database, JWT, Groq, CORS, logging, upload limits). At minimum you need `GROQ_API_KEY` for the AI features to work, and `JWT_SECRET` set to something other than the default for anything beyond local dev.
