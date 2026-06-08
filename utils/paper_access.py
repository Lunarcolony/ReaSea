"""Helpers for open-access / free-to-read paper detection."""

from typing import Any, Dict, Optional


def arxiv_pdf_url(arxiv_id: Optional[str]) -> Optional[str]:
    if not arxiv_id:
        return None
    clean = arxiv_id.replace("arxiv:", "").strip()
    if not clean:
        return None
    return f"https://arxiv.org/pdf/{clean}.pdf"


def resolve_pdf_url(
    pdf_url: Optional[str],
    arxiv_id: Optional[str] = None,
    open_access_url: Optional[str] = None,
) -> Optional[str]:
    if pdf_url:
        return pdf_url
    if arxiv_id:
        return arxiv_pdf_url(arxiv_id)
    return open_access_url


def is_freely_readable(
    *,
    pdf_url: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    source_url: Optional[str] = None,
    is_open_access: bool = False,
    open_access_url: Optional[str] = None,
) -> bool:
    if resolve_pdf_url(pdf_url, arxiv_id, open_access_url):
        return True
    if is_open_access and (open_access_url or source_url):
        return True
    if source_url and "arxiv.org" in source_url.lower():
        return True
    return False


def paper_dict_is_complete(paper: Dict[str, Any]) -> bool:
    title = (paper.get("title") or "").strip()
    authors = (paper.get("authors") or "").strip()
    abstract = (paper.get("full_abstract") or paper.get("abstract_snippet") or "").strip()
    if len(title) < 8 or not authors or len(abstract) < 40:
        return False
    if not is_freely_readable(
        pdf_url=paper.get("pdf_url"),
        arxiv_id=paper.get("arxiv_id"),
        source_url=paper.get("source_url"),
        is_open_access=paper.get("is_open_access", False),
        open_access_url=paper.get("open_access_url"),
    ):
        return False
    return True
