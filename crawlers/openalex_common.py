"""Shared OpenAlex work parsing for crawlers."""

import re
from datetime import datetime
from typing import Any, Dict, Optional

from utils.helpers import reconstruct_openalex_abstract, extract_doi
from utils.openalex_client import normalize_arxiv_id
from utils.paper_access import arxiv_pdf_url


def extract_arxiv_id_from_work(work: Dict[str, Any]) -> Optional[str]:
    ids = work.get("ids", {}) or {}
    arx_raw = ids.get("arxiv")
    if arx_raw:
        return normalize_arxiv_id(str(arx_raw).split("/")[-1])

    locations = [work.get("primary_location")] + (work.get("locations") or [])
    for location in locations:
        if not location:
            continue
        for url in (location.get("landing_page_url"), location.get("pdf_url")):
            if not url:
                continue
            match = re.search(r"arxiv\.org/abs/([^/?#]+)", url, re.IGNORECASE)
            if match:
                return normalize_arxiv_id(match.group(1))
    return None


def openalex_work_to_paper(
    work: Dict[str, Any],
    *,
    source_api: str,
    min_citations: int = 5,
    require_arxiv: bool = False,
) -> Optional[Dict[str, Any]]:
    title = work.get("title")
    if not title:
        return None

    citation_count = int(work.get("cited_by_count") or 0)
    if citation_count < min_citations:
        return None

    openalex_id = work.get("id", "").split("/")[-1] if work.get("id") else None
    if not openalex_id:
        return None

    arxiv_id = extract_arxiv_id_from_work(work)
    if require_arxiv and not arxiv_id:
        return None

    current_year = datetime.now().year
    authors = []
    for authorship in work.get("authorships", []):
        display_name = (authorship.get("author") or {}).get("display_name")
        if display_name:
            authors.append(display_name)

    pub_date_str = work.get("publication_date")
    pub_date = None
    pub_year = current_year
    if pub_date_str:
        pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
        pub_year = pub_date.year

    abstract_text = reconstruct_openalex_abstract(work.get("abstract_inverted_index", {}))
    relevance_score = work.get("relevance_score", 1.0)

    concepts = []
    for concept in work.get("concepts", [])[:10]:
        concepts.append({
            "id": concept.get("id", "").split("/")[-1],
            "name": concept.get("display_name"),
            "score": concept.get("score"),
        })

    primary_location = work.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}
    venue = source.get("display_name", "") or ("arXiv" if arxiv_id else "")
    pdf_url = primary_location.get("pdf_url")

    oa_info = work.get("open_access", {}) or {}
    is_oa = bool(oa_info.get("is_oa"))
    oa_url = oa_info.get("oa_url")
    if not pdf_url and oa_url:
        pdf_url = oa_url
    if arxiv_id and not pdf_url:
        pdf_url = arxiv_pdf_url(arxiv_id)

    if not is_oa and not pdf_url and not arxiv_id:
        return None

    age_years = max((current_year - pub_year), 0.5)
    hybrid_score = relevance_score * ((citation_count + 1) / (age_years + 1))

    source_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else work.get("id")

    return {
        "title": title,
        "authors": ", ".join(authors),
        "abstract_snippet": abstract_text[:500] + "..." if len(abstract_text) > 500 else abstract_text,
        "full_abstract": abstract_text,
        "published_date": pub_date,
        "source_api": source_api,
        "external_id": openalex_id,
        "source_url": source_url,
        "citation_count": citation_count,
        "doi": extract_doi(work),
        "pdf_url": pdf_url,
        "venue": venue,
        "publication_type": work.get("type", ""),
        "openalex_id": openalex_id,
        "arxiv_id": arxiv_id,
        "concepts_json": concepts,
        "is_open_access": is_oa or bool(arxiv_id),
        "hybrid_score": hybrid_score,
    }
