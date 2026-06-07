"""One-time backfill: classify topics and compute metrics for existing papers."""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import init_db, SessionLocal
from models import Paper, PaperTopic, PaperMetrics
from sqlalchemy import or_
from enrichment.enrich_paper import enrich_batch
from classification.metrics import compute_metrics_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BATCH = 500


def backfill_full_abstract(db):
    """Copy abstract_snippet into full_abstract when missing (legacy catalog rows)."""
    q = (
        db.query(Paper)
        .filter(
            or_(Paper.full_abstract.is_(None), Paper.full_abstract == ""),
            Paper.abstract_snippet.isnot(None),
            Paper.abstract_snippet != "",
        )
        .limit(BATCH)
    )
    papers = q.all()
    for p in papers:
        p.full_abstract = p.abstract_snippet.rstrip(".")
    if papers:
        db.commit()
    return len(papers)


def main():
    init_db()
    db = SessionLocal()
    total_papers = db.query(Paper).count()
    logger.info("Bootstrapping catalog for %s papers...", total_papers)

    backfilled = 0
    while True:
        n = backfill_full_abstract(db)
        backfilled += n
        if n:
            logger.info("Backfilled full_abstract for %s papers (total: %s)", n, backfilled)
        if n == 0:
            break

    enriched = 0
    while True:
        n = enrich_batch(db, limit=BATCH, skip_openalex_fetch=True)
        enriched += n
        logger.info("Enriched %s papers (total this run: %s)", n, enriched)
        if n == 0:
            break

    metrics = 0
    while True:
        n = compute_metrics_batch(db, limit=BATCH, only_missing=True)
        metrics += n
        logger.info("Computed metrics for %s papers (total this run: %s)", n, metrics)
        if n == 0:
            break

    topic_count = db.query(PaperTopic).count()
    metric_count = db.query(PaperMetrics).count()
    logger.info("Done. paper_topics=%s, paper_metrics=%s", topic_count, metric_count)
    db.close()


if __name__ == "__main__":
    main()
