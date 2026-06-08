"""Shared OpenAlex HTTP client for metadata and citation lookups."""

import logging
import re
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
DEFAULT_HEADERS = {"User-Agent": "ResearchFeed/1.0 (mailto:researchfeed@example.com)"}


def normalize_arxiv_id(arxiv_id: Optional[str]) -> Optional[str]:
    if not arxiv_id:
        return None
    clean = arxiv_id.replace("arxiv:", "").strip()
    return re.sub(r"v\d+$", "", clean, flags=re.IGNORECASE) or None


def _request(params: Dict[str, Any], max_retries: int = 3, backoff: float = 2.0) -> Optional[Dict[str, Any]]:
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                OPENALEX_WORKS_URL,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=25,
            )
            if response.status_code == 429:
                wait = backoff ** attempt
                logger.warning("OpenAlex rate limited; retrying in %.1fs", wait)
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            if attempt < max_retries:
                wait = backoff ** attempt
                logger.debug("OpenAlex request failed (%s); retrying in %.1fs", exc, wait)
                time.sleep(wait)
            else:
                logger.debug("OpenAlex request failed: %s", exc)
    return None


def work_matches_arxiv(work: Dict[str, Any], arxiv_id: str) -> bool:
    clean = normalize_arxiv_id(arxiv_id)
    if not clean:
        return False

    ids = work.get("ids", {}) or {}
    for value in ids.values():
        if clean in str(value):
            return True

    locations = [work.get("primary_location")] + (work.get("locations") or [])
    for location in locations:
        if not location:
            continue
        url = (location.get("landing_page_url") or "") + (location.get("pdf_url") or "")
        if clean in url:
            return True
    return False


def apply_openalex_work(paper, work: Dict[str, Any]) -> bool:
    """Merge OpenAlex metadata into a Paper row. Returns True if anything changed."""
    from utils.helpers import reconstruct_openalex_abstract, extract_doi

    changed = False
    openalex_id = work.get("id", "").split("/")[-1]
    if openalex_id and paper.openalex_id != openalex_id:
        paper.openalex_id = openalex_id
        changed = True

    doi = extract_doi(work)
    if doi and not paper.doi:
        paper.doi = doi
        changed = True

    cited = work.get("cited_by_count")
    if cited is not None and (paper.citation_count or 0) < int(cited):
        paper.citation_count = int(cited)
        changed = True

    if not paper.full_abstract:
        abstract = reconstruct_openalex_abstract(work.get("abstract_inverted_index", {}))
        if abstract:
            paper.full_abstract = abstract
            if not paper.abstract_snippet:
                paper.abstract_snippet = abstract[:500] + "..." if len(abstract) > 500 else abstract
            changed = True

    if not paper.concepts_json:
        concepts = []
        for concept in work.get("concepts", [])[:10]:
            concepts.append({
                "id": concept.get("id", "").split("/")[-1],
                "name": concept.get("display_name"),
                "score": concept.get("score"),
            })
        if concepts:
            paper.concepts_json = concepts
            changed = True

    primary_location = work.get("primary_location", {}) or {}
    if not paper.venue:
        source = primary_location.get("source", {}) or {}
        venue = source.get("display_name", "")
        if venue:
            paper.venue = venue
            changed = True

    if not paper.pdf_url:
        pdf_url = primary_location.get("pdf_url")
        if pdf_url:
            paper.pdf_url = pdf_url
            changed = True

    oa_info = work.get("open_access", {}) or {}
    if oa_info.get("is_oa"):
        paper.is_open_access = True
        changed = True

    ids = work.get("ids", {}) or {}
    arxiv_raw = ids.get("arxiv")
    if arxiv_raw and not paper.arxiv_id:
        paper.arxiv_id = normalize_arxiv_id(str(arxiv_raw).split("/")[-1])
        changed = True

    return changed


def lookup_work(
    *,
    openalex_id: Optional[str] = None,
    doi: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    title: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Find a single OpenAlex work by ID, DOI, arXiv ID, or title search."""
    if openalex_id:
        clean_id = openalex_id.split("/")[-1]
        data = _request({"filter": f"openalex:{clean_id}", "per-page": 1})
        results = (data or {}).get("results", [])
        if results:
            return results[0]

    if doi:
        data = _request({"filter": f"doi:{doi}", "per-page": 1})
        results = (data or {}).get("results", [])
        if results:
            return results[0]

    clean_arxiv = normalize_arxiv_id(arxiv_id)
    if clean_arxiv:
        data = _request({"search": clean_arxiv, "per-page": 10})
        for work in (data or {}).get("results", []):
            if work_matches_arxiv(work, clean_arxiv):
                return work

    if title:
        data = _request({"search": title, "per-page": 5})
        results = (data or {}).get("results", [])
        if clean_arxiv:
            for work in results:
                if work_matches_arxiv(work, clean_arxiv):
                    return work
        if results:
            title_lower = title.strip().lower()
            for work in results:
                if (work.get("title") or "").strip().lower() == title_lower:
                    return work
            return results[0]

    return None


def fetch_citation_count(
    *,
    openalex_id: Optional[str] = None,
    doi: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    title: Optional[str] = None,
) -> Optional[int]:
    work = lookup_work(openalex_id=openalex_id, doi=doi, arxiv_id=arxiv_id, title=title)
    if not work:
        return None
    count = work.get("cited_by_count")
    return int(count) if count is not None else None
