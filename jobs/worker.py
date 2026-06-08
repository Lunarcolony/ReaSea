"""Scheduled job runner using APScheduler."""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import init_db, SessionLocal
from models import JobRun
from main import run_crawl_cycle
from db_purifier import run_purifier
from enrichment.enrich_paper import enrich_batch, backfill_citations_batch
from classification.metrics import compute_metrics_batch
from embeddings.pipeline import generate_embeddings_batch
from recommender.feed import build_feed

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def log_job_start(db, name: str) -> JobRun:
    run = JobRun(job_name=name, status="running")
    db.add(run)
    db.commit()
    return run


def log_job_finish(db, run: JobRun, status: str, details: dict = None):
    run.status = status
    run.finished_at = datetime.utcnow()
    run.details = details or {}
    db.commit()


def job_crawl():
    db = SessionLocal()
    run = log_job_start(db, "crawl_batch")
    try:
        added = run_crawl_cycle(target_total_papers=50)
        log_job_finish(db, run, "success", {"papers_added": added})
        logger.info("Crawl job done: %s papers added", added)
    except Exception as e:
        log_job_finish(db, run, "failed", {"error": str(e)})
        logger.error("Crawl job failed: %s", e)
    finally:
        db.close()


def job_purify():
    db = SessionLocal()
    run = log_job_start(db, "purify")
    try:
        run_purifier(db)
        log_job_finish(db, run, "success")
    except Exception as e:
        log_job_finish(db, run, "failed", {"error": str(e)})
        logger.error("Purify job failed: %s", e)
    finally:
        db.close()


def job_enrich():
    db = SessionLocal()
    run = log_job_start(db, "enrich")
    try:
        enriched = enrich_batch(db, limit=100)
        citations = backfill_citations_batch(db, limit=50)
        log_job_finish(db, run, "success", {"enriched": enriched, "citations_updated": citations})
        logger.info("Enrichment job done: %s papers enriched, %s citations updated", enriched, citations)
    except Exception as e:
        log_job_finish(db, run, "failed", {"error": str(e)})
        logger.error("Enrich job failed: %s", e)
    finally:
        db.close()


def job_metrics():
    db = SessionLocal()
    run = log_job_start(db, "compute_metrics")
    try:
        count = compute_metrics_batch(db, limit=500)
        log_job_finish(db, run, "success", {"computed": count})
        logger.info("Metrics job done: %s papers", count)
    except Exception as e:
        log_job_finish(db, run, "failed", {"error": str(e)})
        logger.error("Metrics job failed: %s", e)
    finally:
        db.close()


def job_embeddings():
    db = SessionLocal()
    run = log_job_start(db, "generate_embeddings")
    try:
        count = generate_embeddings_batch(db, limit=50)
        log_job_finish(db, run, "success", {"embedded": count})
        logger.info("Embeddings job done: %s papers", count)
    except Exception as e:
        log_job_finish(db, run, "failed", {"error": str(e)})
        logger.error("Embeddings job failed: %s", e)
    finally:
        db.close()


def job_precompute_feed():
    db = SessionLocal()
    run = log_job_start(db, "precompute_feed")
    try:
        rows = build_feed(db, user_id=None)
        log_job_finish(db, run, "success", {"rows": len(rows)})
        logger.info("Feed precompute done: %s rows", len(rows))
    except Exception as e:
        log_job_finish(db, run, "failed", {"error": str(e)})
        logger.error("Feed precompute failed: %s", e)
    finally:
        db.close()


def main():
    init_db()
    scheduler = BlockingScheduler()
    scheduler.add_job(job_crawl, IntervalTrigger(minutes=30), id="crawl", max_instances=1)
    scheduler.add_job(job_purify, IntervalTrigger(minutes=15), id="purify", max_instances=1)
    scheduler.add_job(job_enrich, IntervalTrigger(minutes=20), id="enrich", max_instances=1)
    scheduler.add_job(job_metrics, IntervalTrigger(minutes=60), id="metrics", max_instances=1)
    scheduler.add_job(job_embeddings, IntervalTrigger(minutes=45), id="embeddings", max_instances=1)
    scheduler.add_job(job_precompute_feed, IntervalTrigger(minutes=30), id="feed", max_instances=1)

    logger.info("Starting job scheduler...")
    # Run initial jobs once at startup
    job_purify()
    job_enrich()
    job_metrics()
    scheduler.start()


if __name__ == "__main__":
    main()
