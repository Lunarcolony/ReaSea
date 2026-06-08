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

You only need **two** shortcuts:

| Action | Double-click |
|--------|----------------|
| **Website** (API + UI) | **`Start Website.bat`** |
| **Crawlers** (background ingestion) | **`Start Crawlers.bat`** |

To stop: **`Stop Website.bat`** or **`Stop Crawlers.bat`**.

Older names (`Start Research Feed.bat`, `Start Crawler and Purifier.bat`) still work and open the same launchers.

### Start Website

Double-click **`Start Website.bat`** in the project folder.

1. Creates the Python virtual environment and installs dependencies on first run (if missing)
2. Runs `npm install` in `frontend/` on first run (if missing)
3. Frees ports **8000** and **3000** if an old session is still running
4. Opens two windows:
   - **Research Feed API** — FastAPI backend at http://127.0.0.1:8000
   - **Research Feed UI** — Next.js frontend at http://localhost:3000
5. Waits for both services, then opens your browser to http://localhost:3000

### Start Crawlers (cooperative pipeline)

Double-click **`Start Crawlers.bat`**. One window runs everything **in order** (no competing loops):

1. **Crawl** new papers (OpenAlex + arXiv)
2. **Backfill citations** for arXiv papers via OpenAlex
3. **Enrich** topics and authors
4. **Compute metrics** for recommendations
5. **Purify** the database (after backfill, so papers are not deleted too early)
6. **Refresh feed cache** (every 2nd cycle)
7. **Generate embeddings** (every 3rd cycle)

Then it sleeps ~5 minutes and repeats. On first start it also merges any stray database files into `data/papers.db`.

Semantic Scholar is disabled; only reliable APIs (OpenAlex + arXiv) are used.

### Pin to desktop (optional)

1. Right-click **`Start Website.bat`**
2. Choose **Show more options → Send to → Desktop (create shortcut)**
3. Rename the shortcut to **Research Feed** (optional)
4. Double-click the desktop shortcut anytime to start the app

### Manual launch (alternative)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-app.ps1
powershell -ExecutionPolicy Bypass -File scripts/stop-app.ps1
```

## Database (single SQLite file)

All components (API, crawlers, purifier, db viewer) use **one canonical database**:

`data/papers.db` (absolute path — never depends on your terminal folder)

Your original `papers.db` in the project root is **preserved as a backup copy**. On first run, it is copied into `data/papers.db` if needed.

If counts look wrong after an upgrade, run once:

```bash
python scripts/consolidate_databases.py
```

This merges any stray `.db` files into `data/papers.db` without deleting source files. The purifier also creates a timestamped backup under `data/backups/` before each run.

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
| `DATABASE_URL` | PostgreSQL connection string (default: absolute SQLite at `data/papers.db`) |
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
