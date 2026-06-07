# Research Feed — Netflix for Research Papers

A personalized research paper discovery platform with crawlers, classification, embeddings, recommendation feed, and a Netflix-style UI.

## Architecture

```
Crawlers (OpenAlex, Semantic Scholar)
    → PostgreSQL + pgvector
    → Enrichment + Classification + Metrics + Embeddings
    → FastAPI (feed, search, auth)
    → Next.js frontend
```

## One-Click Launch (Windows)

Double-click **`Start Research Feed.bat`** in the project folder. No terminal commands needed.

### What it does

1. Creates the Python virtual environment and installs dependencies on first run (if missing)
2. Runs `npm install` in `frontend/` on first run (if missing)
3. Frees ports **8000** and **3000** if an old session is still running
4. Opens two windows:
   - **Research Feed API** — FastAPI backend at http://127.0.0.1:8000
   - **Research Feed UI** — Next.js frontend at http://localhost:3000
5. Waits for both services, then opens your browser to http://localhost:3000

To shut down, close the two server windows or double-click **`Stop Research Feed.bat`**.

### Pin to desktop (optional)

1. Right-click **`Start Research Feed.bat`**
2. Choose **Show more options → Send to → Desktop (create shortcut)**
3. Rename the shortcut to **Research Feed** (optional)
4. Double-click the desktop shortcut anytime to start the app

### Manual launch (alternative)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-app.ps1
powershell -ExecutionPolicy Bypass -File scripts/stop-app.ps1
```

## Quick Start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Local Development (SQLite fallback)

```bash
pip install -r requirements.txt
python -c "from database import init_db; init_db()"
python main.py                    # Run one crawl cycle
python db_purifier.py             # Clean data
uvicorn api.main:app --reload     # Start API on :8000

cd frontend && npm install && npm run dev   # Frontend on :3000
```

## Bootstrap Existing Catalog

After upgrading schema or importing legacy papers, run once to classify topics and compute metrics:

```bash
python scripts/bootstrap_catalog.py
```

## Scheduled Jobs

```bash
python jobs/worker.py
```

Runs on intervals: crawl (30m), purify (15m), enrich (20m), metrics (60m), embeddings (45m).

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (default: sqlite) |
| `SECRET_KEY` | JWT signing key |
| `CORS_ORIGINS` | Allowed frontend origins |
| `EMBEDDING_MODEL` | sentence-transformers model name |
| `NEXT_PUBLIC_API_URL` | API URL for frontend |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/feed` | Homepage feed rows (personalized for local user) |
| GET | `/papers/{id}` | Paper detail + similar |
| GET | `/search?q=` | Hybrid search |
| GET/PATCH | `/users/me/preferences` | Topic interests (no auth) |
| POST | `/users/me/events` | Track views/saves |
| GET/POST | `/users/me/reading-list` | Saved papers |

No sign-in required — the app uses a single local user created automatically on startup.

## Feed Rows

- **Trending Now** — citation velocity × recency × engagement
- **Recommended for You** — hybrid content + topic matching (cold start via onboarding)
- **High Impact** — top hybrid impact scores
- **Topic carousels** — from user preferences or config topics
- **Because You Read** — embedding similarity to last viewed paper

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
├── api/              FastAPI backend
├── crawlers/         Paper ingestion (OpenAlex, Semantic Scholar)
├── enrichment/       Post-crawl metadata enrichment
├── classification/   Topic classification + metrics
├── embeddings/       Sentence-transformer pipeline
├── recommender/      Feed orchestrator + MMR diversification
├── jobs/             APScheduler worker
├── frontend/         Next.js Netflix-style UI
├── taxonomy/         OpenAlex → topic mapping
└── tests/
```
