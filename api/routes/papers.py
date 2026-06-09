from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Paper, PaperMetrics, User
from api.single_user import get_default_user
from recommender.feed import paper_to_dict, similar_papers, get_metrics_map
from utils.display import paper_abstract_snippet

router = APIRouter()


@router.get("/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db), user: User = Depends(get_default_user)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    metrics = db.query(PaperMetrics).filter(PaperMetrics.paper_id == paper_id).first()
    similar = similar_papers(db, paper_id, limit=8)
    metrics_map = get_metrics_map(db, [p.id for p in similar])
    data = paper_to_dict(paper, metrics)
    data.update({
        "full_abstract": paper.full_abstract or paper_abstract_snippet(paper, max_len=5000),
        "doi": paper.doi,
        "venue": paper.venue,
        "publication_type": paper.publication_type,
        "saved": False,
        "similar": [paper_to_dict(p, metrics_map.get(p.id)) for p in similar],
    })
    return data
