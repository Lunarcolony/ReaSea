import requests
from datetime import datetime
from .base import BaseCrawler
from utils.helpers import reconstruct_openalex_abstract, extract_doi


class OpenAlexCrawler(BaseCrawler):
    def __init__(self, limit: int = 10, query: str = "artificial intelligence", offset: int = 0, ingestion_topic: str = ""):
        super().__init__(limit, query, offset, ingestion_topic)
        self.base_url = "https://api.openalex.org/works"

    def fetch_papers(self):
        page = (self.offset // self.limit) + 1
        filter_str = "cited_by_count:>0,is_paratext:false"
        fetch_limit = min(self.limit * 2, 100)

        params = {
            "search": self.query,
            "filter": filter_str,
            "sort": "relevance_score:desc",
            "per-page": fetch_limit,
            "page": page,
        }
        headers = {"User-Agent": "ResearchFeedCrawler/1.0 (mailto:test@example.com)"}
        response = requests.get(self.base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        raw_papers = []
        current_year = datetime.now().year

        for work in data.get("results", []):
            title = work.get("title")
            if not title:
                continue

            authors = []
            for authorship in work.get("authorships", []):
                author = authorship.get("author", {})
                display_name = author.get("display_name")
                if display_name:
                    authors.append(display_name)

            pub_date_str = work.get("publication_date")
            pub_date = None
            pub_year = current_year
            if pub_date_str:
                pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").date()
                pub_year = pub_date.year

            abstract_text = reconstruct_openalex_abstract(work.get("abstract_inverted_index", {}))
            openalex_id = work.get("id", "").split("/")[-1] if work.get("id") else None
            citation_count = work.get("cited_by_count", 0)
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
            venue = source.get("display_name", "")
            pdf_url = primary_location.get("pdf_url")
            pub_type = work.get("type", "")

            ids = work.get("ids", {}) or {}
            arxiv_id = (ids.get("arxiv") or "").replace("https://arxiv.org/abs/", "") or None

            age_years = max((current_year - pub_year), 0.5)
            hybrid_score = relevance_score * ((citation_count + 1) / (age_years + 1))

            raw_papers.append({
                "title": title,
                "authors": ", ".join(authors),
                "abstract_snippet": abstract_text[:500] + "..." if len(abstract_text) > 500 else abstract_text,
                "full_abstract": abstract_text,
                "published_date": pub_date,
                "source_api": "OpenAlex",
                "external_id": openalex_id,
                "source_url": work.get("id"),
                "citation_count": citation_count,
                "doi": extract_doi(work),
                "pdf_url": pdf_url,
                "venue": venue,
                "publication_type": pub_type,
                "openalex_id": openalex_id,
                "arxiv_id": arxiv_id,
                "concepts_json": concepts,
                "hybrid_score": hybrid_score,
            })

        sorted_papers = sorted(raw_papers, key=lambda x: x["hybrid_score"], reverse=True)
        return self._finalize(sorted_papers[: self.limit])
