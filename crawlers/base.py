from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# Standard paper dict keys returned by all crawlers
PAPER_KEYS = {
    "title", "authors", "abstract_snippet", "published_date",
    "source_api", "external_id", "source_url", "citation_count",
}

OPTIONAL_PAPER_KEYS = {
    "full_abstract", "doi", "pdf_url", "venue", "publication_type",
    "openalex_id", "arxiv_id", "pmid", "primary_topic", "concepts_json",
    "fields_of_study", "ingestion_topic", "hybrid_score",
}


def normalize_paper(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Strip unknown keys and ensure abstract_snippet from full_abstract if missing."""
    paper = {k: raw[k] for k in PAPER_KEYS if k in raw}
    for k in OPTIONAL_PAPER_KEYS:
        if k in raw and raw[k] is not None:
            paper[k] = raw[k]
    if not paper.get("abstract_snippet") and paper.get("full_abstract"):
        full = paper["full_abstract"]
        paper["abstract_snippet"] = full[:500] + "..." if len(full) > 500 else full
    elif paper.get("abstract_snippet") and not paper.get("full_abstract"):
        paper["full_abstract"] = paper["abstract_snippet"].rstrip(".")
    return paper


class BaseCrawler(ABC):
    def __init__(self, limit: int = 10, query: str = "", offset: int = 0, ingestion_topic: str = ""):
        self.limit = limit
        self.query = query
        self.offset = offset
        self.ingestion_topic = ingestion_topic

    @abstractmethod
    def fetch_papers(self) -> List[Dict[str, Any]]:
        pass

    def _finalize(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for p in papers:
            if self.ingestion_topic:
                p["ingestion_topic"] = self.ingestion_topic
            p.pop("hybrid_score", None)
            result.append(normalize_paper(p))
        return result
