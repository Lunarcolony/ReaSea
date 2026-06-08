"""
Cooperative ingestion pipeline (single process, ordered steps).

Each cycle runs in this order so steps do not fight each other:
  1. Crawl new papers (OpenAlex + arXiv)
  2. Backfill citations for arXiv papers via OpenAlex
  3. Enrich topics and authors
  4. Compute recommendation metrics
  5. Purify database (after PDF/citation backfill)
  6. Refresh feed cache (every N cycles)
  7. Generate embeddings (every N cycles)
"""

import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import init_db, SessionLocal
from models import Paper
from main import run_crawl_cycle
from db_purifier import run_purifier
from enrichment.enrich_paper import enrich_batch, backfill_citations_batch
from classification.metrics import compute_metrics_batch
from embeddings.pipeline import generate_embeddings_batch
from recommender.feed import build_feed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pipeline")

CYCLE_SLEEP_SECONDS = int(os.environ.get("PIPELINE_SLEEP_SECONDS", "300"))
CRAWL_TARGET = int(os.environ.get("PIPELINE_CRAWL_TARGET", "50"))
CITATION_BATCH_SIZE = int(os.environ.get("PIPELINE_CITATION_BATCH", "50"))
CITATION_BATCHES_PER_CYCLE = int(os.environ.get("PIPELINE_CITATION_BATCHES", "3"))
ENRICH_LIMIT = int(os.environ.get("PIPELINE_ENRICH_LIMIT", "100"))
METRICS_LIMIT = int(os.environ.get("PIPELINE_METRICS_LIMIT", "500"))
EMBED_EVERY_N_CYCLES = int(os.environ.get("PIPELINE_EMBED_EVERY", "3"))
FEED_EVERY_N_CYCLES = int(os.environ.get("PIPELINE_FEED_EVERY", "2"))
LOCK_FILE = ROOT / "data" / "pipeline.lock"


def _write_lock() -> None:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _remove_lock() -> None:
    LOCK_FILE.unlink(missing_ok=True)


def bootstrap() -> None:
    logger.info("Initializing database...")
    init_db()

    try:
        from scripts.consolidate_databases import main as consolidate_databases

        logger.info("Checking for stray database files to merge...")
        consolidate_databases()
    except Exception as exc:
        logger.warning("Database consolidation skipped: %s", exc)


def run_citation_backfill() -> int:
    db = SessionLocal()
    total = 0
    try:
        for _ in range(CITATION_BATCHES_PER_CYCLE):
            updated = backfill_citations_batch(db, limit=CITATION_BATCH_SIZE)
            total += updated
            if updated == 0:
                break
    finally:
        db.close()
    return total


def run_enrichment() -> int:
    db = SessionLocal()
    try:
        return enrich_batch(db, limit=ENRICH_LIMIT)
    finally:
        db.close()


def run_metrics() -> int:
    db = SessionLocal()
    try:
        return compute_metrics_batch(db, limit=METRICS_LIMIT)
    finally:
        db.close()


def run_purification() -> int:
    db = SessionLocal()
    try:
        run_purifier(db)
        return db.query(Paper).count()
    finally:
        db.close()


def run_feed_refresh() -> int:
    db = SessionLocal()
    try:
        rows = build_feed(db, user_id=None)
        return len(rows)
    finally:
        db.close()


def run_embeddings() -> int:
    db = SessionLocal()
    try:
        return generate_embeddings_batch(db, limit=50)
    finally:
        db.close()


def run_pipeline_cycle(cycle_num: int) -> dict:
    results = {}

    logger.info("[1/7] Crawling new papers...")
    results["papers_added"] = run_crawl_cycle(target_total_papers=CRAWL_TARGET)

    logger.info("[2/7] Backfilling citations from OpenAlex...")
    results["citations_updated"] = run_citation_backfill()

    logger.info("[3/7] Enriching topics and authors...")
    results["enriched"] = run_enrichment()

    logger.info("[4/7] Computing recommendation metrics...")
    results["metrics_updated"] = run_metrics()

    logger.info("[5/7] Purifying database...")
    results["papers_total"] = run_purification()

    if cycle_num % FEED_EVERY_N_CYCLES == 0:
        logger.info("[6/7] Refreshing feed cache...")
        results["feed_rows"] = run_feed_refresh()
    else:
        logger.info("[6/7] Skipping feed refresh this cycle (runs every %s cycles)", FEED_EVERY_N_CYCLES)

    if cycle_num % EMBED_EVERY_N_CYCLES == 0:
        logger.info("[7/7] Generating embeddings...")
        results["embeddings"] = run_embeddings()
    else:
        logger.info("[7/7] Skipping embeddings this cycle (runs every %s cycles)", EMBED_EVERY_N_CYCLES)

    return results


def main() -> None:
    if LOCK_FILE.exists():
        existing_pid = LOCK_FILE.read_text(encoding="utf-8").strip()
        logger.error(
            "Pipeline already running (PID %s). Stop it first with Stop Crawlers.bat.",
            existing_pid,
        )
        sys.exit(1)

    _write_lock()
    logger.info("Research Feed cooperative pipeline started (PID %s)", os.getpid())
    logger.info(
        "Cycle order: crawl -> citations -> enrich -> metrics -> purify -> feed -> embeddings"
    )
    logger.info("Sleeping %s seconds between cycles.", CYCLE_SLEEP_SECONDS)

    try:
        bootstrap()
        cycle = 0
        while True:
            cycle += 1
            logger.info("========== Pipeline cycle %s ==========", cycle)
            try:
                results = run_pipeline_cycle(cycle)
                logger.info(
                    "Cycle %s done: added=%s citations=%s enriched=%s total_papers=%s",
                    cycle,
                    results.get("papers_added", 0),
                    results.get("citations_updated", 0),
                    results.get("enriched", 0),
                    results.get("papers_total", "?"),
                )
            except Exception:
                logger.exception("Cycle %s failed; continuing after sleep.", cycle)

            logger.info("Next cycle in %s seconds...", CYCLE_SLEEP_SECONDS)
            time.sleep(CYCLE_SLEEP_SECONDS)
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user.")
    finally:
        _remove_lock()


if __name__ == "__main__":
    main()
