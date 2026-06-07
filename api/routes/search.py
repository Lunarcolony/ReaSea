from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from database import get_db
from models import Paper, PaperMetrics
from recommender.feed import paper_to_dict, get_metrics_map
from embeddings.pipeline import embed_text, get_paper_embedding, cosine_similarity

router = APIRouter()


@router.get("")
def search_papers(
    q: str = Query("", min_length=0),
    topic: Optional[str] = None,
    min_citations: int = 0,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
):
    query = db.query(Paper)
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(Paper.title.ilike(term), Paper.authors.ilike(term), Paper.abstract_snippet.ilike(term))
        )
    if topic:
        query = query.filter(Paper.primary_topic == topic)
    if min_citations:
        query = query.filter(Paper.citation_count >= min_citations)

    total = query.count()
    papers = query.order_by(desc(Paper.published_date)).offset((page - 1) * per_page).limit(per_page).all()

    # Semantic re-rank when query provided
    if q and len(q) > 3:
        try:
            q_emb = embed_text(q)
            scored = []
            for p in papers:
                p_emb = get_paper_embedding(p)
                sim = cosine_similarity(q_emb, p_emb) if p_emb else 0
                scored.append((p, sim))
            scored.sort(key=lambda x: -x[1])
            papers = [p for p, _ in scored]
        except Exception:
            pass

    metrics_map = get_metrics_map(db, [p.id for p in papers])
    return {
        "papers": [paper_to_dict(p, metrics_map.get(p.id)) for p in papers],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }
