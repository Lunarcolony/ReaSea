"""Utility helpers for paper ingestion."""

import re
from typing import Any, Dict, List, Optional


def slugify_topic(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def reconstruct_openalex_abstract(inverted: Dict[str, List[int]]) -> str:
    if not inverted:
        return ""
    try:
        words = max(max(pos) for pos in inverted.values()) + 1
        abstract_arr = [""] * words
        for word, positions in inverted.items():
            for pos in positions:
                abstract_arr[pos] = word
        return " ".join(abstract_arr)
    except Exception:
        return ""


def extract_doi(work: Dict[str, Any]) -> Optional[str]:
    doi = work.get("doi")
    if doi:
        return doi.replace("https://doi.org/", "")
    ids = work.get("ids", {}) or {}
    return (ids.get("doi") or "").replace("https://doi.org/", "") or None


def paper_fields_for_db(p_data: Dict[str, Any]) -> Dict[str, Any]:
    """Filter dict to only keys valid for Paper model."""
    from models import Paper
    valid = {c.name for c in Paper.__table__.columns}
    return {k: v for k, v in p_data.items() if k in valid and k not in ("id", "created_at", "updated_at")}
