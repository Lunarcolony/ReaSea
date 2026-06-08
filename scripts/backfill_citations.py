"""One-time batch update of citation counts from OpenAlex."""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import init_db, SessionLocal
from enrichment.enrich_paper import backfill_citations_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main(batch_size: int = 50, max_batches: int = 20):
    init_db()
    db = SessionLocal()
    total = 0
    try:
        for batch in range(max_batches):
            updated = backfill_citations_batch(db, limit=batch_size)
            total += updated
            logger.info("Batch %s: updated %s papers (running total: %s)", batch + 1, updated, total)
            if updated == 0:
                break
    finally:
        db.close()
    logger.info("Citation backfill complete. Updated %s papers.", total)


if __name__ == "__main__":
    main()
