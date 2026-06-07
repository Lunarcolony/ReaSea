import json
import logging
import time
import random
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from database import init_db, SessionLocal
from models import Paper, CrawlerState
from utils.helpers import paper_fields_for_db, slugify_topic

from crawlers.openalex_crawler import OpenAlexCrawler
from crawlers.semantic_scholar_crawler import SemanticScholarCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CRAWLER_CLASSES = {
    "OpenAlexCrawler": OpenAlexCrawler,
    "SemanticScholarCrawler": SemanticScholarCrawler,
}

fetched_offset_zero = set()


def load_config():
    try:
        with open("crawler_config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "crawlers": {
                "OpenAlexCrawler": {"enabled": True, "batch_size": 10},
                "SemanticScholarCrawler": {"enabled": True, "batch_size": 5},
            },
            "topics": [{"name": "Machine Learning", "queries": {"default": "machine learning"}}],
            "global_settings": {"delay_seconds": 2.0, "max_retries": 3, "retry_backoff_factor": 2.0, "resume": True},
        }


def run_crawl_cycle(target_total_papers: int = 50) -> int:
    """Run one crawl cycle. Returns count of papers added."""
    init_db()
    config = load_config()
    global_settings = config.get("global_settings", {})
    delay_seconds = global_settings.get("delay_seconds", 2.0)
    max_retries = global_settings.get("max_retries", 3)
    retry_backoff_factor = global_settings.get("retry_backoff_factor", 2.0)
    resume = global_settings.get("resume", True)

    db = SessionLocal()
    total_added = 0

    try:
        enabled_crawlers = [n for n, cfg in config.get("crawlers", {}).items() if cfg.get("enabled", True)]
        topics_list = config.get("topics", [])
        if not enabled_crawlers or not topics_list:
            logger.warning("No active crawlers or topics defined.")
            return 0

        papers_gathered = 0
        logger.info("--- Starting crawl cycle (target: %s papers) ---", target_total_papers)

        while papers_gathered < target_total_papers:
            selected_topic = random.choice(topics_list)
            selected_crawler_name = random.choice(enabled_crawlers)
            topic_name = selected_topic.get("name")
            queries = selected_topic.get("queries", {})
            crawler_class = CRAWLER_CLASSES.get(selected_crawler_name)
            if not crawler_class:
                continue

            query = queries.get(selected_crawler_name) or queries.get("default")
            if not query:
                continue

            crawler_cfg = config.get("crawlers", {}).get(selected_crawler_name, {})
            batch_size = crawler_cfg.get("batch_size", 10)
            current_limit = min(batch_size, target_total_papers - papers_gathered)

            state_record = None
            if resume:
                state_record = db.query(CrawlerState).filter(
                    CrawlerState.crawler_name == selected_crawler_name,
                    CrawlerState.topic_name == topic_name,
                    CrawlerState.query == query,
                ).first()

            combo_key = (selected_crawler_name, topic_name, query)
            if combo_key in fetched_offset_zero:
                offset = state_record.last_offset if state_record else 0
                is_offset_zero_run = False
            else:
                offset = 0
                is_offset_zero_run = True

            logger.info(
                "[CRAWL] Topic='%s' via %s (offset=%s, limit=%s)",
                topic_name, selected_crawler_name, offset, current_limit,
            )

            crawler = crawler_class(
                limit=current_limit, query=query, offset=offset,
                ingestion_topic=slugify_topic(topic_name),
            )

            papers_data = []
            retries = 0
            success = False
            while retries <= max_retries:
                try:
                    papers_data = crawler.fetch_papers()
                    success = True
                    break
                except Exception as e:
                    is_rate_limit = "429" in str(e) or "too many requests" in str(e).lower()
                    if is_rate_limit and retries < max_retries:
                        wait_time = delay_seconds * (retry_backoff_factor ** retries)
                        logger.warning("Rate limited. Retrying in %.1fs...", wait_time)
                        time.sleep(wait_time)
                        retries += 1
                    else:
                        logger.error("Error fetching '%s': %s", topic_name, e)
                        break

            if not success:
                continue

            if not papers_data:
                if is_offset_zero_run:
                    fetched_offset_zero.add(combo_key)
                elif resume and state_record:
                    state_record.last_offset = 0
                    db.commit()
                continue

            added_in_batch = 0
            for p_data in papers_data:
                if not p_data.get("external_id"):
                    continue
                if not p_data.get("primary_topic") and p_data.get("ingestion_topic"):
                    p_data["primary_topic"] = p_data["ingestion_topic"]

                fields = paper_fields_for_db(p_data)
                paper = Paper(**fields)
                db.add(paper)
                try:
                    db.commit()
                    added_in_batch += 1
                    total_added += 1
                except IntegrityError:
                    db.rollback()

            logger.info("-> Added %s/%s papers from '%s'.", added_in_batch, len(papers_data), topic_name)
            papers_gathered += added_in_batch

            if is_offset_zero_run:
                fetched_offset_zero.add(combo_key)
                if resume and not state_record:
                    state_record = CrawlerState(
                        crawler_name=selected_crawler_name,
                        topic_name=topic_name,
                        query=query,
                        last_offset=len(papers_data),
                    )
                    db.add(state_record)
                    db.commit()
            else:
                new_offset = offset + len(papers_data)
                if resume:
                    if not state_record:
                        state_record = CrawlerState(
                            crawler_name=selected_crawler_name,
                            topic_name=topic_name,
                            query=query,
                            last_offset=new_offset,
                        )
                        db.add(state_record)
                    else:
                        state_record.last_offset = new_offset
                    db.commit()

            time.sleep(delay_seconds)

    except Exception as e:
        logger.error("Unexpected error in crawl cycle: %s", e)
    finally:
        db.close()

    logger.info("Crawl cycle finished. Added %s new papers.", total_added)
    return total_added


if __name__ == "__main__":
    run_crawl_cycle()
