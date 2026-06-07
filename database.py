import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///papers.db",
)

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
