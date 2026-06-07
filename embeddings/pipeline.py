"""Generate and store paper embeddings."""

import logging
import os
from typing import List, Optional

from sqlalchemy.orm import Session

import os
from models import Paper, USE_PGVECTOR

logger = logging.getLogger(__name__)

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _model = SentenceTransformer(model_name)
    return _model


def paper_text(paper: Paper) -> str:
    abstract = paper.full_abstract or paper.abstract_snippet or ""
    return f"{paper.title or ''}. {abstract}".strip()


def embed_text(text: str) -> List[float]:
    model = get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def set_paper_embedding(paper: Paper, vector: List[float]) -> None:
    if USE_PGVECTOR and hasattr(paper, "embedding"):
        paper.embedding = vector
    else:
        paper.embedding_json = vector


def get_paper_embedding(paper: Paper) -> Optional[List[float]]:
    if USE_PGVECTOR and getattr(paper, "embedding", None) is not None:
        return list(paper.embedding)
    if paper.embedding_json:
        return paper.embedding_json
    return None


def generate_embeddings_batch(db: Session, limit: int = 50) -> int:
    if USE_PGVECTOR:
        papers = db.query(Paper).filter(Paper.embedding.is_(None)).limit(limit).all()
    else:
        papers = db.query(Paper).filter(Paper.embedding_json.is_(None)).limit(limit).all()

    count = 0
    for paper in papers:
        text = paper_text(paper)
        if not text or len(text) < 10:
            continue
        try:
            vector = embed_text(text)
            set_paper_embedding(paper, vector)
            db.commit()
            count += 1
        except Exception as e:
            logger.error("Embedding failed for paper %s: %s", paper.id, e)
            db.rollback()
    return count


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return dot  # vectors are normalized
