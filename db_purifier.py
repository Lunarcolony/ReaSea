import logging
import re
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Paper

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def remove_missing_titles(db: Session) -> int:
    papers = db.query(Paper).filter(
        (Paper.title == None) | (Paper.title == "") | (Paper.title.is_(None))
    ).all()
    count = len(papers)
    for p in papers:
        db.delete(p)
    if count:
        db.commit()
    return count


def remove_placeholder_titles(db: Session) -> int:
    contains_patterns = [
        "title pending", "title not available", "title unavailable",
        "unknown title", "Crossref", "placeholder",
    ]
    exact_patterns = ["untitled", "n/a", "[no title]", "(no title)", "null", "none", "Crossref"]
    count = 0
    for pattern in contains_patterns:
        papers = db.query(Paper).filter(func.lower(Paper.title).contains(pattern.lower())).all()
        for p in papers:
            db.delete(p)
            count += 1
    for pattern in exact_patterns:
        papers = db.query(Paper).filter(func.lower(func.trim(Paper.title)) == pattern.lower()).all()
        for p in papers:
            db.delete(p)
            count += 1
    if count:
        db.commit()
    return count


def remove_duplicate_titles(db: Session) -> int:
    dupes = db.query(func.lower(Paper.title)).group_by(func.lower(Paper.title)).having(func.count(Paper.id) > 1).all()
    count = 0
    for (title_lower,) in dupes:
        papers = db.query(Paper).filter(func.lower(Paper.title) == title_lower).order_by(Paper.id).all()
        for p in papers[1:]:
            db.delete(p)
            count += 1
    if count:
        db.commit()
    return count


def remove_duplicate_external_ids(db: Session) -> int:
    dupes = db.query(Paper.external_id).group_by(Paper.external_id).having(func.count(Paper.id) > 1).all()
    count = 0
    for (ext_id,) in dupes:
        papers = db.query(Paper).filter(Paper.external_id == ext_id).order_by(Paper.id).all()
        for p in papers[1:]:
            db.delete(p)
            count += 1
    if count:
        db.commit()
    return count


def remove_very_short_titles(db: Session) -> int:
    papers = db.query(Paper).filter(func.length(func.trim(Paper.title)) < 5).all()
    count = len(papers)
    for p in papers:
        db.delete(p)
    if count:
        db.commit()
    return count


def remove_html_artifact_titles(db: Session) -> int:
    html_pattern = re.compile(r"<[^>]+>|&[a-zA-Z]+;|&#\d+;")
    papers = db.query(Paper).all()
    count = 0
    for p in papers:
        if p.title and html_pattern.search(p.title):
            db.delete(p)
            count += 1
    if count:
        db.commit()
    return count


def clean_whitespace_in_titles(db: Session) -> int:
    papers = db.query(Paper).all()
    count = 0
    for p in papers:
        if p.title:
            cleaned = re.sub(r"\s+", " ", p.title).strip()
            if cleaned != p.title:
                p.title = cleaned
                count += 1
    if count:
        db.commit()
    return count


def remove_missing_external_ids(db: Session) -> int:
    papers = db.query(Paper).filter(
        (Paper.external_id == "") | (Paper.external_id.is_(None))
    ).all()
    count = len(papers)
    for p in papers:
        db.delete(p)
    if count:
        db.commit()
    return count


def remove_missing_source_api(db: Session) -> int:
    papers = db.query(Paper).filter(
        (Paper.source_api == None) | (Paper.source_api == "") | (Paper.source_api.is_(None))
    ).all()
    count = len(papers)
    for p in papers:
        db.delete(p)
    if count:
        db.commit()
    return count


def clean_abstract_html(db: Session) -> int:
    html_tag_pattern = re.compile(r"<[^>]+>")
    papers = db.query(Paper).filter(Paper.abstract_snippet != None).all()
    count = 0
    for p in papers:
        if p.abstract_snippet and html_tag_pattern.search(p.abstract_snippet):
            cleaned = html_tag_pattern.sub("", p.abstract_snippet).strip()
            if cleaned != p.abstract_snippet:
                p.abstract_snippet = cleaned
                count += 1
        if p.full_abstract and html_tag_pattern.search(p.full_abstract):
            p.full_abstract = html_tag_pattern.sub("", p.full_abstract).strip()
            count += 1
    if count:
        db.commit()
    return count


PURIFICATION_RULES = [
    ("Remove papers with missing titles", remove_missing_titles),
    ("Remove papers with placeholder titles", remove_placeholder_titles),
    ("Remove papers with very short titles", remove_very_short_titles),
    ("Remove papers with HTML in titles", remove_html_artifact_titles),
    ("Remove duplicate titles (keep oldest)", remove_duplicate_titles),
    ("Remove duplicate external IDs (keep oldest)", remove_duplicate_external_ids),
    ("Remove papers with missing external IDs", remove_missing_external_ids),
    ("Remove papers with missing source API", remove_missing_source_api),
    ("Normalize whitespace in titles", clean_whitespace_in_titles),
    ("Strip HTML tags from abstracts", clean_abstract_html),
]


def run_purifier(db: Session = None):
    from database import SessionLocal
    own_session = db is None
    if own_session:
        db = SessionLocal()

    total_before = db.query(Paper).count()
    logger.info("Starting purification. Total papers: %s", total_before)
    total_deleted = 0
    total_cleaned = 0

    for rule_name, rule_fn in PURIFICATION_RULES:
        try:
            affected = rule_fn(db)
            is_cleaning = any(kw in rule_name.lower() for kw in ["normalize", "strip", "clean"])
            if is_cleaning:
                total_cleaned += affected
            else:
                total_deleted += affected
        except Exception as e:
            logger.error("Rule '%s' failed: %s", rule_name, e)
            db.rollback()

    total_after = db.query(Paper).count()
    logger.info("Purification complete: %s -> %s (deleted %s, cleaned %s)", total_before, total_after, total_deleted, total_cleaned)

    if own_session:
        db.close()


if __name__ == "__main__":
    run_purifier()
