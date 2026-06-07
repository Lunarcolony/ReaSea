import requests
from datetime import datetime, date
from .base import BaseCrawler


class SemanticScholarCrawler(BaseCrawler):
    def __init__(self, limit: int = 10, query: str = "machine learning", offset: int = 0, ingestion_topic: str = ""):
        super().__init__(limit, query, offset, ingestion_topic)
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    def fetch_papers(self):
        fetch_limit = min(self.limit * 2, 100)
        params = {
            "query": self.query,
            "limit": fetch_limit,
            "offset": self.offset,
            "fields": "title,authors,abstract,year,externalIds,url,citationCount,relevanceScore,fieldsOfStudy,publicationVenue,openAccessPdf",
        }
        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        raw_papers = []
        current_year = datetime.now().year

        for item in data.get("data", []):
            title = item.get("title")
            if not title:
                continue

            citation_count = item.get("citationCount", 0)
            if citation_count < 1:
                continue

            abstract = item.get("abstract") or ""
            authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
            year = item.get("year")
            pub_date = date(year, 1, 1) if year else None
            pub_year = year if year else current_year

            external_id = item.get("paperId")
            if not external_id:
                continue

            external_ids = item.get("externalIds", {}) or {}
            doi = external_ids.get("DOI")
            arxiv_id = external_ids.get("ArXiv")
            pubmed_id = external_ids.get("PubMed")

            venue_obj = item.get("publicationVenue", {}) or {}
            venue = venue_obj.get("name", "")
            pdf_obj = item.get("openAccessPdf", {}) or {}
            pdf_url = pdf_obj.get("url")

            fields = item.get("fieldsOfStudy") or []
            relevance_score = item.get("relevanceScore", 1.0)
            age_years = max((current_year - pub_year), 0.5)
            hybrid_score = relevance_score * ((citation_count + 1) / (age_years + 1))

            raw_papers.append({
                "title": title,
                "authors": ", ".join(authors),
                "abstract_snippet": abstract[:500] + "..." if len(abstract) > 500 else abstract,
                "full_abstract": abstract,
                "published_date": pub_date,
                "source_api": "SemanticScholar",
                "external_id": external_id,
                "source_url": item.get("url"),
                "citation_count": citation_count,
                "doi": doi,
                "arxiv_id": arxiv_id,
                "pmid": pubmed_id,
                "pdf_url": pdf_url,
                "venue": venue,
                "fields_of_study": fields,
                "hybrid_score": hybrid_score,
            })

        sorted_papers = sorted(raw_papers, key=lambda x: x["hybrid_score"], reverse=True)
        return self._finalize(sorted_papers[: self.limit])
