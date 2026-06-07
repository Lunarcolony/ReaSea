from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import User, UserPreference, UserEvent, SavedPaper, Paper
from api.schemas import PreferencesUpdate, EventsBatch
from api.single_user import get_default_user
from recommender.feed import paper_to_dict, get_metrics_map
from embeddings.pipeline import get_paper_embedding

router = APIRouter()


@router.get("/me/preferences")
def get_preferences(user: User = Depends(get_default_user), db: Session = Depends(get_db)):
    pref = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    return {
        "topic_slugs": pref.topic_slugs if pref else [],
        "research_role": user.research_role,
    }


@router.patch("/me/preferences")
def update_preferences(body: PreferencesUpdate, user: User = Depends(get_default_user), db: Session = Depends(get_db)):
    pref = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    if not pref:
        pref = UserPreference(user_id=user.id, topic_slugs=body.topic_slugs)
        db.add(pref)
    else:
        pref.topic_slugs = body.topic_slugs
    if body.research_role:
        user.research_role = body.research_role
    db.commit()
    return {"topic_slugs": pref.topic_slugs, "research_role": user.research_role}


@router.post("/me/events")
def record_events(body: EventsBatch, user: User = Depends(get_default_user), db: Session = Depends(get_db)):
    pref = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    if not pref:
        pref = UserPreference(user_id=user.id, topic_slugs=[])
        db.add(pref)
        db.flush()

    for item in body.events:
        db.add(UserEvent(
            user_id=user.id,
            paper_id=item.paper_id,
            event_type=item.event_type,
            read_time_seconds=item.read_time_seconds,
        ))
        paper = db.query(Paper).filter(Paper.id == item.paper_id).first()
        if not paper:
            continue

        if item.event_type == "save":
            exists = db.query(SavedPaper).filter(
                SavedPaper.user_id == user.id, SavedPaper.paper_id == item.paper_id
            ).first()
            if not exists:
                db.add(SavedPaper(user_id=user.id, paper_id=item.paper_id))

        if item.event_type in ("save", "click", "view"):
            emb = get_paper_embedding(paper)
            if emb:
                weight = {"save": 1.0, "click": 0.6, "view": 0.3}.get(item.event_type, 0.3)
                if pref.embedding_centroid:
                    pref.embedding_centroid = [
                        (o * (1 - weight) + e * weight) for o, e in zip(pref.embedding_centroid, emb)
                    ]
                else:
                    pref.embedding_centroid = emb

            if paper.primary_topic and paper.primary_topic not in (pref.topic_slugs or []):
                if item.event_type in ("save", "click"):
                    slugs = list(pref.topic_slugs or [])
                    if paper.primary_topic not in slugs:
                        slugs.insert(0, paper.primary_topic)
                        pref.topic_slugs = slugs[:8]

    db.commit()
    return {"recorded": len(body.events)}


@router.get("/me/reading-list")
def reading_list(user: User = Depends(get_default_user), db: Session = Depends(get_db)):
    saved = db.query(SavedPaper).filter(SavedPaper.user_id == user.id).order_by(desc(SavedPaper.created_at)).all()
    paper_ids = [s.paper_id for s in saved]
    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all() if paper_ids else []
    paper_map = {p.id: p for p in papers}
    metrics_map = get_metrics_map(db, paper_ids)
    return {
        "papers": [
            paper_to_dict(paper_map[pid], metrics_map.get(pid))
            for pid in paper_ids if pid in paper_map
        ]
    }


@router.post("/me/reading-list/{paper_id}")
def save_paper(paper_id: int, user: User = Depends(get_default_user), db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    exists = db.query(SavedPaper).filter(SavedPaper.user_id == user.id, SavedPaper.paper_id == paper_id).first()
    if not exists:
        db.add(SavedPaper(user_id=user.id, paper_id=paper_id))
        db.add(UserEvent(user_id=user.id, paper_id=paper_id, event_type="save"))
        db.commit()
    return {"saved": True}


@router.delete("/me/reading-list/{paper_id}")
def unsave_paper(paper_id: int, user: User = Depends(get_default_user), db: Session = Depends(get_db)):
    saved = db.query(SavedPaper).filter(SavedPaper.user_id == user.id, SavedPaper.paper_id == paper_id).first()
    if saved:
        db.delete(saved)
        db.commit()
    return {"saved": False}
