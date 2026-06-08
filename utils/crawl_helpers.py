"""Helpers for crawl deduplication and quality settings."""

from typing import Optional

from sqlalchemy.orm import Session

from models import Paper
from utils.openalex_client import normalize_arxiv_id


def get_min_citations(config: dict) -> int:
    return max(int(config.get("global_settings", {}).get("min_citations", 5)), 0)


def paper_already_in_db(db: Session, p_data: dict) -> Optional[str]:
    """Return reason string if paper is already stored, else None."""
    external_id = p_data.get("external_id")
    if external_id:
        if db.query(Paper.id).filter(Paper.external_id == external_id).first():
            return "external_id"

    openalex_id = p_data.get("openalex_id")
    if openalex_id and openalex_id != "unresolved":
        if db.query(Paper.id).filter(Paper.openalex_id == openalex_id).first():
            return "openalex_id"

    doi = p_data.get("doi")
    if doi:
        if db.query(Paper.id).filter(Paper.doi == doi).first():
            return "doi"

    arxiv_id = p_data.get("arxiv_id")
    if arxiv_id:
        clean = normalize_arxiv_id(arxiv_id)
        variants = {arxiv_id, clean, f"arxiv:{clean}", f"arxiv:{arxiv_id}"}
        if db.query(Paper.id).filter(Paper.arxiv_id.in_(variants)).first():
            return "arxiv_id"
        if db.query(Paper.id).filter(Paper.external_id.in_(variants)).first():
            return "external_id"

    return None
