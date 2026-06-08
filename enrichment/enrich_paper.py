"""Post-crawl enrichment: topics, authors, cross-source linking."""

import logging
import time
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import exists, or_

from models import Paper, PaperTopic, Author, PaperAuthor
from utils.helpers import slugify_topic
from utils.openalex_client import apply_openalex_work, lookup_work
from classification.topics import classify_paper_topics

logger = logging.getLogger(__name__)

OPENALEX_LOOKUP_DELAY = 0.35


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
        already_linked = db.query(PaperAuthor).filter(
            PaperAuthor.paper_id == paper.id, PaperAuthor.author_id == author.id
        ).first()
        if not already_linked:
            db.add(PaperAuthor(paper_id=paper.id, author_id=author.id, position=position))
            position += 1


def enrich_from_openalex(db: Session, paper: Paper) -> bool:
    """Backfill metadata and citations from OpenAlex by arXiv ID, DOI, OpenAlex ID, or title."""
    if paper.openalex_id == "unresolved":
        return False

    needs_metadata = not (paper.openalex_id and paper.concepts_json)
    needs_citations = (paper.citation_count or 0) == 0

    if not needs_metadata and not needs_citations:
        return False

    work = lookup_work(
        openalex_id=paper.openalex_id,
        doi=paper.doi,
        arxiv_id=paper.arxiv_id,
        title=paper.title if needs_citations or needs_metadata else None,
    )
    if not work:
        return False

    return apply_openalex_work(paper, work)


def apply_topic_tags(db: Session, paper: Paper) -> None:
    topics = classify_paper_topics(paper)
    for topic_slug, confidence, source in topics:
        already_tagged = db.query(PaperTopic).filter(
            PaperTopic.paper_id == paper.id, PaperTopic.topic_slug == topic_slug
        ).first()
        if not already_tagged:
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


def backfill_citations_batch(db: Session, limit: int = 50) -> int:
    """Fill missing citation counts from OpenAlex (especially arXiv-ingested papers)."""
    papers = (
        db.query(Paper)
        .filter(
            Paper.citation_count == 0,
            Paper.openalex_id.is_(None),
            or_(
                Paper.arxiv_id.isnot(None),
                Paper.doi.isnot(None),
            ),
        )
        .order_by(Paper.id.desc())
        .limit(limit)
        .all()
    )

    updated = 0
    for paper in papers:
        paper_id = paper.id
        before = paper.citation_count or 0
        try:
            work = lookup_work(
                doi=paper.doi,
                arxiv_id=paper.arxiv_id,
                title=paper.title,
            )
            if work:
                apply_openalex_work(paper, work)
            elif not paper.openalex_id:
                paper.openalex_id = "unresolved"
            db.commit()
            if (paper.citation_count or 0) > before:
                updated += 1
            time.sleep(OPENALEX_LOOKUP_DELAY)
        except Exception as e:
            logger.error("Citation backfill failed for paper %s: %s", paper_id, e)
            db.rollback()
    return updated
