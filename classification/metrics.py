"""Compute paper quality and impact metrics."""

import logging
import math
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import exists

from models import Paper, PaperMetrics, UserEvent

logger = logging.getLogger(__name__)

VENUE_TIERS = {
    "nature": 1.0, "science": 1.0, "cell": 0.95, "lancet": 0.95,
    "neurips": 0.9, "icml": 0.9, "cvpr": 0.9, "iclr": 0.9,
    "jama": 0.9, "pnas": 0.85, "ieee": 0.7, "acm": 0.7,
}


def venue_tier(venue: str) -> float:
    if not venue:
        return 0.5
    v = venue.lower()
    for key, tier in VENUE_TIERS.items():
        if key in v:
            return tier
    return 0.5


def compute_metrics_for_paper(paper: Paper, engagement: float = 0.0) -> PaperMetrics:
    current_year = datetime.now().year
    pub_year = paper.published_date.year if paper.published_date else current_year
    age_years = max((current_year - pub_year), 0.5)

    citation_velocity = (paper.citation_count or 0) / age_years
    recency_score = math.exp(-age_years / 5.0)
    hybrid_impact = citation_velocity * recency_score
    v_tier = venue_tier(paper.venue or "")
    trending_score = citation_velocity * recency_score * (1 + engagement) * v_tier

    return PaperMetrics(
        paper_id=paper.id,
        hybrid_impact=hybrid_impact,
        citation_velocity=citation_velocity,
        recency_score=recency_score,
        venue_tier=v_tier,
        engagement_score=engagement,
        trending_score=trending_score,
    )


def engagement_for_paper(db: Session, paper_id: int) -> float:
    events = db.query(UserEvent).filter(UserEvent.paper_id == paper_id).all()
    score = 0.0
    weights = {"view": 0.1, "click": 0.2, "save": 1.0, "dismiss": -0.5}
    for e in events:
        score += weights.get(e.event_type, 0)
    return max(score, 0.0)


def compute_metrics_batch(db: Session, limit: int = 500, only_missing: bool = True) -> int:
    query = db.query(Paper)
    if only_missing:
        query = query.filter(~exists().where(PaperMetrics.paper_id == Paper.id))
    papers = query.limit(limit).all()
    count = 0
    for paper in papers:
        engagement = engagement_for_paper(db, paper.id)
        metrics = db.query(PaperMetrics).filter(PaperMetrics.paper_id == paper.id).first()
        computed = compute_metrics_for_paper(paper, engagement)
        if metrics:
            metrics.hybrid_impact = computed.hybrid_impact
            metrics.citation_velocity = computed.citation_velocity
            metrics.recency_score = computed.recency_score
            metrics.venue_tier = computed.venue_tier
            metrics.engagement_score = computed.engagement_score
            metrics.trending_score = computed.trending_score
        else:
            db.add(computed)
        count += 1
    try:
        db.commit()
    except Exception:
        db.rollback()
        return 0
    return count
