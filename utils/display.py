"""Shared display helpers for API responses."""

from models import Paper


def paper_abstract_snippet(paper: Paper, max_len: int = 320) -> str:
    text = (paper.abstract_snippet or "").strip()
    if not text and paper.full_abstract:
        text = paper.full_abstract.strip()
    if not text:
        return "Abstract not available. Open the paper to read more from the source."
    text = text.rstrip(".")
    if len(text) > max_len:
        return text[:max_len].rsplit(" ", 1)[0] + "..."
    return text


def format_topic(slug: str | None) -> str | None:
    if not slug:
        return None
    return slug.replace("-", " ").title()
