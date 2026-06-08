import os
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

from paths import PROJECT_ROOT, DATA_DIR, LEGACY_DB_PATH, CANONICAL_DB_PATH


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _bootstrap_canonical_sqlite() -> Path:
    """
    Ensure one canonical DB file exists under data/papers.db.
    If the legacy root papers.db exists, copy it into place (never delete the legacy file).
    """
    _ensure_data_dir()
    if CANONICAL_DB_PATH.exists():
        return CANONICAL_DB_PATH

    if LEGACY_DB_PATH.exists():
        shutil.copy2(LEGACY_DB_PATH, CANONICAL_DB_PATH)
        return CANONICAL_DB_PATH

    CANONICAL_DB_PATH.touch()
    return CANONICAL_DB_PATH


def resolve_database_url() -> str:
    """Return DATABASE_URL, defaulting to an absolute SQLite path under data/."""
    env_url = os.getenv("DATABASE_URL", "").strip()
    if env_url:
        return env_url

    db_path = _bootstrap_canonical_sqlite()
    # Absolute path required so cwd changes (bat files, uvicorn, crawlers) never create a second DB.
    return f"sqlite:///{db_path.resolve().as_posix()}"


DATABASE_URL = resolve_database_url()

connect_args = {}
engine_kwargs = {"echo": False}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 5

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Columns added after initial SQLite schema
SQLITE_MIGRATIONS = [
    ("papers", "full_abstract", "TEXT"),
    ("papers", "doi", "VARCHAR"),
    ("papers", "pdf_url", "VARCHAR"),
    ("papers", "venue", "VARCHAR"),
    ("papers", "publication_type", "VARCHAR"),
    ("papers", "openalex_id", "VARCHAR"),
    ("papers", "arxiv_id", "VARCHAR"),
    ("papers", "pmid", "VARCHAR"),
    ("papers", "primary_topic", "VARCHAR"),
    ("papers", "concepts_json", "JSON"),
    ("papers", "fields_of_study", "JSON"),
    ("papers", "ingestion_topic", "VARCHAR"),
    ("papers", "is_open_access", "BOOLEAN DEFAULT 0"),
    ("papers", "embedding_json", "JSON"),
    ("papers", "updated_at", "DATETIME"),
]


def _migrate_sqlite():
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    with engine.connect() as conn:
        for table, column, col_type in SQLITE_MIGRATIONS:
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        conn.commit()


def backup_sqlite_database(label: str = "manual") -> Path | None:
    """Create a timestamped backup of the canonical SQLite file. Never deletes the live DB."""
    if not DATABASE_URL.startswith("sqlite"):
        return None
    db_path = CANONICAL_DB_PATH if CANONICAL_DB_PATH.exists() else LEGACY_DB_PATH
    if not db_path.exists():
        return None
    _ensure_data_dir()
    backups_dir = DATA_DIR / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = backups_dir / f"papers_{label}_{stamp}.db"
    shutil.copy2(db_path, dest)
    # Keep only the 5 most recent backups
    existing = sorted(backups_dir.glob("papers_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in existing[5:]:
        old.unlink(missing_ok=True)
    return dest


def get_db_info() -> dict:
    """Return paths used by the app (for debugging / admin scripts)."""
    return {
        "project_root": str(PROJECT_ROOT),
        "database_url": DATABASE_URL,
        "canonical_db": str(CANONICAL_DB_PATH),
        "legacy_db": str(LEGACY_DB_PATH),
        "legacy_exists": LEGACY_DB_PATH.exists(),
        "canonical_exists": CANONICAL_DB_PATH.exists(),
    }


def init_db():
    """Create tables and enable pgvector extension when using PostgreSQL."""
    if DATABASE_URL.startswith("postgresql"):
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    from models import Paper, CrawlerState, PaperTopic, PaperMetrics  # noqa: F401
    from models import Author, PaperAuthor, User, UserPreference, UserEvent  # noqa: F401
    from models import SavedPaper, FeedCache, JobRun  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
