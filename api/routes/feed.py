from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from api.single_user import get_default_user
from recommender.feed import build_feed, topic_row, trending_row, for_you_row, high_impact_row, paper_to_dict, get_metrics_map

router = APIRouter()


@router.get("")
def get_feed(
    refresh: bool = False,
    user: User = Depends(get_default_user),
    db: Session = Depends(get_db),
):
    return build_feed(db, user_id=user.id, refresh=refresh)


@router.get("/rows/{row_id}")
def get_feed_row(row_id: str, user: User = Depends(get_default_user), db: Session = Depends(get_db)):
    papers = []
    title = row_id.replace("_", " ").title()

    if row_id == "trending":
        papers = trending_row(db)
        title = "Trending Now"
    elif row_id == "for_you":
        papers = for_you_row(db, user.id)
        title = "Recommended for You"
    elif row_id == "high_impact":
        papers = high_impact_row(db)
        title = "High Impact"
    elif row_id.startswith("topic_"):
        slug = row_id.replace("topic_", "")
        papers = topic_row(db, slug)
        title = slug.replace("-", " ").title()

    metrics_map = get_metrics_map(db, [p.id for p in papers])
    return {
        "id": row_id,
        "title": title,
        "papers": [paper_to_dict(p, metrics_map.get(p.id)) for p in papers],
    }
