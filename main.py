import json
import logging
import time
import random
import os
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from database import init_db, SessionLocal
from models import Paper
from utils.helpers import paper_fields_for_db, slugify_topic
from utils.crawl_helpers import get_min_citations, paper_already_in_db

from crawlers.openalex_crawler import OpenAlexCrawler
from crawlers.arxiv_crawler import ArxivCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CRAWLER_CLASSES = {
    "OpenAlexCrawler": OpenAlexCrawler,
    "ArxivCrawler": ArxivCrawler,
}

fetched_offset_zero = set()
MAX_EMPTY_BATCHES = 25
OFFSETS_FILE = "crawler_offsets.json"


def load_config():
    try:
        with open("crawler_config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "crawlers": {
                "OpenAlexCrawler": {"enabled": True, "batch_size": 10},
                "ArxivCrawler": {"enabled": True, "batch_size": 10},
            },
            "topics": [{"name": "Machine Learning", "queries": {"default": "machine learning"}}],
            "global_settings": {
                "delay_seconds": 3.0,
                "max_retries": 3,
                "retry_backoff_factor": 2.0,
                "resume": True,
                "min_citations": 5,
            },
        }


def load_offsets():
    if not os.path.exists(OFFSETS_FILE):
        return {}
    try:
        with open(OFFSETS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_offsets(offsets_dict):
    try:
        with open(OFFSETS_FILE, "w") as f:
            json.dump(offsets_dict, f, indent=2)
    except Exception as e:
        logger.error("Failed to save offsets to file: %s", e)


def _advance_offset(resume, offset, step, is_offset_zero_run, combo_key, offsets_dict):
    if is_offset_zero_run:
        fetched_offset_zero.add(combo_key)
    if not resume:
        return offset
    new_offset = offset + step
    
    key_str = f"{combo_key[0]}|{combo_key[1]}|{combo_key[2]}"
    offsets_dict[key_str] = new_offset
    save_offsets(offsets_dict)
    
    return new_offset


def run_crawl_cycle(target_total_papers: int = 50) -> int:
    """Run one crawl cycle. Returns count of papers added."""
    init_db()
    config = load_config()
    global_settings = config.get("global_settings", {})
    delay_seconds = global_settings.get("delay_seconds", 3.0)
    max_retries = global_settings.get("max_retries", 3)
    retry_backoff_factor = global_settings.get("retry_backoff_factor", 2.0)
    resume = global_settings.get("resume", True)
    min_citations = get_min_citations(config)

    db = SessionLocal()
    total_added = 0
    empty_batches = 0
    
    offsets_dict = load_offsets()

    try:
        enabled_crawlers = [n for n, cfg in config.get("crawlers", {}).items() if cfg.get("enabled", True)]
        topics_list = config.get("topics", [])
        if not enabled_crawlers or not topics_list:
            logger.warning("No active crawlers or topics defined.")
            return 0

        papers_gathered = 0
        logger.info(
            "--- Starting crawl cycle (target: %s papers, min citations: %s) ---",
            target_total_papers,
            min_citations,
        )

        while papers_gathered < target_total_papers:
            if empty_batches >= MAX_EMPTY_BATCHES:
                logger.warning(
                    "Stopping early: %s consecutive batches added nothing (catalog likely caught up).",
                    empty_batches,
                )
                break

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

            combo_key = (selected_crawler_name, topic_name, query)
            key_str = f"{combo_key[0]}|{combo_key[1]}|{combo_key[2]}"
            
            if combo_key in fetched_offset_zero:
                offset = offsets_dict.get(key_str, 0) if resume else 0
                is_offset_zero_run = False
            else:
                offset = 0
                is_offset_zero_run = True

            logger.info(
                "[CRAWL] Topic='%s' via %s (offset=%s, limit=%s)",
                topic_name, selected_crawler_name, offset, current_limit,
            )

            crawler = crawler_class(
                limit=current_limit,
                query=query,
                offset=offset,
                ingestion_topic=slugify_topic(topic_name),
                min_citations=min_citations,
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
                empty_batches += 1
                continue

            # Force exact limit matching to keep pages aligned nicely
            offset_step = max(current_limit, batch_size)

            if not papers_data:
                logger.info(
                    "-> No new quality papers at this offset for '%s' (min %s citations). Advancing offset.",
                    topic_name,
                    min_citations,
                )
                _advance_offset(
                    resume, offset, offset_step, is_offset_zero_run, combo_key, offsets_dict
                )
                empty_batches += 1
                time.sleep(delay_seconds)
                continue

            added_in_batch = 0
            duplicate_count = 0
            for p_data in papers_data:
                if not p_data.get("external_id"):
                    continue
                if not p_data.get("primary_topic") and p_data.get("ingestion_topic"):
                    p_data["primary_topic"] = p_data["ingestion_topic"]

                dup_reason = paper_already_in_db(db, p_data)
                if dup_reason:
                    duplicate_count += 1
                    continue

                fields = paper_fields_for_db(p_data)
                paper = Paper(**fields)
                db.add(paper)
                try:
                    db.commit()
                    added_in_batch += 1
                    total_added += 1
                except IntegrityError:
                    db.rollback()
                    duplicate_count += 1

            if added_in_batch == 0:
                empty_batches += 1
            else:
                empty_batches = 0

            logger.info(
                "-> Added %s/%s from '%s' (%s already in catalog, min citations %s).",
                added_in_batch,
                len(papers_data),
                topic_name,
                duplicate_count,
                min_citations,
            )
            papers_gathered += added_in_batch

            _advance_offset(
                resume, offset, offset_step, is_offset_zero_run, combo_key, offsets_dict
            )

            time.sleep(delay_seconds)

    except Exception as e:
        logger.error("Unexpected error in crawl cycle: %s", e)
    finally:
        db.close()

    logger.info("Crawl cycle finished. Added %s new papers.", total_added)
    return total_added


if __name__ == "__main__":
    run_crawl_cycle()
