"""
Merge papers from any stray SQLite files into the canonical data/papers.db.
Never deletes source database files — only copies missing records in.
"""

import logging
import sqlite3
import sys
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paths import PROJECT_ROOT, CANONICAL_DB_PATH, LEGACY_DB_PATH, DATA_DIR
from database import init_db, SessionLocal, backup_sqlite_database, get_db_info
from models import Paper
from sqlalchemy.exc import IntegrityError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SKIP_DIRS = {".venv", "venv", "node_modules", ".next", "backups"}


def find_sqlite_files() -> list[Path]:
    found = []
    for path in PROJECT_ROOT.rglob("*.db"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        found.append(path)
    return sorted(set(found))


def count_papers(path: Path) -> int:
    if not path.exists():
        return 0
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def merge_from_sqlite(source: Path) -> int:
    """Copy papers missing from canonical DB (match on external_id)."""
    if source.resolve() == CANONICAL_DB_PATH.resolve():
        return 0

    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM papers").fetchall()
    except sqlite3.Error as e:
        logger.warning("Skipping %s: %s", source, e)
        return 0
    finally:
        conn.close()

    if not rows:
        return 0

    added = 0
    db = SessionLocal()
    try:
        valid_cols = {c.name for c in Paper.__table__.columns}
        skip_cols = {"id", "created_at", "updated_at", "embedding", "embedding_json"}
        for row in rows:
            data = {k: row[k] for k in row.keys() if k in valid_cols and k not in skip_cols}
            if not data.get("external_id") or not data.get("title"):
                continue
            if "published_date" in data:
                data["published_date"] = parse_date(data["published_date"])
            paper = Paper(**data)
            db.add(paper)
            try:
                db.commit()
                added += 1
            except IntegrityError:
                db.rollback()
    finally:
        db.close()
    return added


def main():
    init_db()
    info = get_db_info()
    logger.info("Database configuration: %s", info)

    backup = backup_sqlite_database("pre_consolidate")
    if backup:
        logger.info("Safety backup created: %s", backup)

    canonical_count = count_papers(CANONICAL_DB_PATH)
    legacy_count = count_papers(LEGACY_DB_PATH) if LEGACY_DB_PATH.exists() else 0
    logger.info("Canonical DB %s has %s papers", CANONICAL_DB_PATH, canonical_count)
    if legacy_count:
        logger.info("Legacy DB %s has %s papers (kept, not deleted)", LEGACY_DB_PATH, legacy_count)

    total_added = 0

    # Merge legacy root DB only if it has more papers than canonical
    if LEGACY_DB_PATH.exists() and legacy_count > canonical_count:
        logger.info("Legacy DB has more papers — merging into canonical...")
        added = merge_from_sqlite(LEGACY_DB_PATH)
        total_added += added
        logger.info("  -> added %s from legacy", added)
        canonical_count = count_papers(CANONICAL_DB_PATH)

    for path in find_sqlite_files():
        if path.resolve() == CANONICAL_DB_PATH.resolve():
            continue
        if path.resolve() == LEGACY_DB_PATH.resolve() and legacy_count <= canonical_count:
            continue
        n = count_papers(path)
        if n == 0:
            continue
        logger.info("Merging from %s (%s papers)...", path, n)
        added = merge_from_sqlite(path)
        total_added += added
        logger.info("  -> added %s new unique papers", added)

    final_count = count_papers(CANONICAL_DB_PATH)
    logger.info(
        "Consolidation complete. Canonical papers: %s -> %s (+%s merged)",
        canonical_count,
        final_count,
        total_added,
    )
    logger.info("Legacy file preserved at: %s", LEGACY_DB_PATH)
    logger.info("All apps should use: %s", CANONICAL_DB_PATH)


if __name__ == "__main__":
    main()
