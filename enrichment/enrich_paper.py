"""Post-crawl enrichment: topics, authors, cross-source linking."""

import logging
from typing import Optional

import requests
from sqlalchemy.orm import Session
from sqlalchemy import exists

from models import Paper, PaperTopic, Author, PaperAuthor
from utils.helpers import slugify_topic, reconstruct_openalex_abstract, extract_doi
from classification.topics import classify_paper_topics

logger = logging.getLogger(__name__)


def link_authors(db: Session, paper: Paper) -> None:
    if not paper.authors:
        return
    names = [n.strip() for n in paper.authors.split(",") if n.strip()]
    seen_author_ids = set()
    position = 0
    for name in names:
        author = db.query(Author).filter(Author.name == name).first()
        if not author:
            author = Author(name=name)
            db.add(author)
            db.flush()
        if author.id in seen_author_ids:
            continue
        seen_author_ids.add(author.id)
        exists = db.query(PaperAuthor).filter(
            PaperAuthor.paper_id == paper.id, PaperAuthor.author_id == author.id
        ).first()
        if not exists:
            db.add(PaperAuthor(paper_id=paper.id, author_id=author.id, position=position))
            position += 1


def enrich_from_openalex(db: Session, paper: Paper) -> bool:
    """Backfill metadata from OpenAlex by DOI or title."""
    if paper.openalex_id and paper.concepts_json:
        return False

    params = {}
    if paper.doi:
        params["filter"] = f"doi:{paper.doi}"
    elif paper.title:
        params["search"] = paper.title
        params["per-page"] = 1
    else:
        return False

    headers = {"User-Agent": "ResearchFeedCrawler/1.0 (mailto:test@example.com)"}
    try:
        resp = requests.get("https://api.openalex.org/works", params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return False
        work = results[0]
    except Exception as e:
        logger.debug("OpenAlex backfill failed for paper %s: %s", paper.id, e)
        return False

    paper.openalex_id = work.get("id", "").split("/")[-1]
    paper.doi = paper.doi or extract_doi(work)
    if not paper.full_abstract:
        paper.full_abstract = reconstruct_openalex_abstract(work.get("abstract_inverted_index", {}))
        if paper.full_abstract and not paper.abstract_snippet:
            paper.abstract_snippet = (
                paper.full_abstract[:500] + "..." if len(paper.full_abstract) > 500 else paper.full_abstract
            )

    concepts = []
    for concept in work.get("concepts", [])[:10]:
        concepts.append({
            "id": concept.get("id", "").split("/")[-1],
            "name": concept.get("display_name"),
            "score": concept.get("score"),
        })
    paper.concepts_json = concepts

    primary_location = work.get("primary_location", {}) or {}
    if not paper.venue:
        source = primary_location.get("source", {}) or {}
        paper.venue = source.get("display_name", "")
    if not paper.pdf_url:
        paper.pdf_url = primary_location.get("pdf_url")

    return True


def apply_topic_tags(db: Session, paper: Paper) -> None:
    topics = classify_paper_topics(paper)
    for topic_slug, confidence, source in topics:
        exists = db.query(PaperTopic).filter(
            PaperTopic.paper_id == paper.id, PaperTopic.topic_slug == topic_slug
        ).first()
        if not exists:
            db.add(PaperTopic(paper_id=paper.id, topic_slug=topic_slug, confidence=confidence, source=source))
    if topics and not paper.primary_topic:
        paper.primary_topic = topics[0][0]


def enrich_paper(db: Session, paper: Paper, skip_openalex_fetch: bool = False) -> None:
    if not skip_openalex_fetch:
        enrich_from_openalex(db, paper)
    if paper.ingestion_topic and not paper.primary_topic:
        paper.primary_topic = paper.ingestion_topic
    apply_topic_tags(db, paper)
    link_authors(db, paper)


def enrich_batch(db: Session, limit: int = 100, skip_openalex_fetch: bool = False) -> int:
    """Enrich papers missing topics. Uses keyword classification without API when skip_openalex_fetch=True."""
    papers = (
        db.query(Paper)
        .filter(~exists().where(PaperTopic.paper_id == Paper.id))
        .limit(limit)
        .all()
    )

    count = 0
    for paper in papers:
        paper_id = paper.id
        try:
            enrich_paper(db, paper, skip_openalex_fetch=skip_openalex_fetch)
            db.commit()
            count += 1
        except Exception as e:
            logger.error("Enrichment failed for paper %s: %s", paper_id, e)
            db.rollback()
    return count
