import requests

from .base import BaseCrawler
from .openalex_common import openalex_work_to_paper


class ArxivCrawler(BaseCrawler):
    """Fetch cited arXiv preprints via OpenAlex (min citations, free full text)."""

    def __init__(
        self,
        limit: int = 10,
        query: str = "machine learning",
        offset: int = 0,
        ingestion_topic: str = "",
        min_citations: int = 5,
    ):
        super().__init__(limit, query, offset, ingestion_topic, min_citations=min_citations)
        self.base_url = "https://api.openalex.org/works"

    def fetch_papers(self):
        page = (self.offset // max(self.limit, 1)) + 1
        min_c = max(self.min_citations, 1)
        filter_str = (
            f"cited_by_count:>{min_c - 1},is_paratext:false,open_access.is_oa:true"
        )
        fetch_limit = min(self.limit * 5, 100)

        params = {
            "search": self.query,
            "filter": filter_str,
            "sort": "cited_by_count:desc",
            "per-page": fetch_limit,
            "page": page,
        }
        headers = {"User-Agent": "ResearchFeedCrawler/1.0 (mailto:researchfeed@example.com)"}
        response = requests.get(self.base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        raw_papers = []
        for work in response.json().get("results", []):
            paper = openalex_work_to_paper(
                work,
                source_api="arXiv",
                min_citations=self.min_citations,
                require_arxiv=True,
            )
            if paper:
                raw_papers.append(paper)

        sorted_papers = sorted(
            raw_papers,
            key=lambda x: x.get("citation_count", 0),
            reverse=True,
        )
        return self._finalize(sorted_papers[: self.limit])
