"""Topic classification using OpenAlex concepts and keyword rules."""

import json
import os
from typing import List, Tuple

from models import Paper

TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "..", "taxonomy", "openalex_map.json")


def load_taxonomy() -> dict:
    with open(TAXONOMY_PATH, "r") as f:
        return json.load(f)


def classify_paper_topics(paper: Paper) -> List[Tuple[str, float, str]]:
    """Return list of (topic_slug, confidence, source)."""
    taxonomy = load_taxonomy()
    results = {}

    # From ingestion topic
    if paper.ingestion_topic:
        slug = paper.ingestion_topic
        if slug in taxonomy or True:
            results[slug] = max(results.get(slug, 0), 0.9)

    # From OpenAlex concepts
    if paper.concepts_json:
        concept_ids = {c.get("id") for c in paper.concepts_json if c.get("id")}
        for slug, meta in taxonomy.items():
            oa_ids = set(meta.get("openalex_concepts", []))
            overlap = concept_ids & oa_ids
            if overlap:
                best_score = max(
                    (c.get("score", 0.5) for c in paper.concepts_json if c.get("id") in overlap),
                    default=0.5,
                )
                results[slug] = max(results.get(slug, 0), float(best_score))

    # Keyword fallback on title + abstract
    text = f"{paper.title or ''} {(paper.full_abstract or paper.abstract_snippet or '')}".lower()
    for slug, meta in taxonomy.items():
        for kw in meta.get("keywords", []):
            if kw.lower() in text:
                results[slug] = max(results.get(slug, 0), 0.6)
                break

    # Fields of study from Semantic Scholar
    if paper.fields_of_study:
        fos_lower = {f.lower() for f in paper.fields_of_study}
        for slug, meta in taxonomy.items():
            label = meta.get("label", "").lower()
            if label in fos_lower or any(kw.lower() in fos_lower for kw in meta.get("keywords", [])):
                results[slug] = max(results.get(slug, 0), 0.7)

    if not results and paper.primary_topic:
        results[paper.primary_topic] = 0.5

    source = "openalex" if paper.concepts_json else "classifier"
    if paper.ingestion_topic and paper.ingestion_topic in results:
        source = "crawler"

    classified = [(slug, conf, source) for slug, conf in sorted(results.items(), key=lambda x: -x[1])]
    if not classified:
        classified = [("general-research", 0.3, "classifier")]
    return classified
