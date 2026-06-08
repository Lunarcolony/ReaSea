"""Netflix-style feed recommendation engine with YouTube-like personalization."""

import hashlib
import json
import logging
import os
import random
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import Paper, PaperMetrics, PaperTopic, UserPreference, UserEvent, SavedPaper, FeedCache
from embeddings.pipeline import get_paper_embedding, cosine_similarity

logger = logging.getLogger(__name__)

ROW_LIMIT = 24
POOL_MULTIPLIER = 8
SESSION_ROW_ID = "__feed_session__"
EVENT_WEIGHTS = {"click": 3.0, "view": 1.0, "save": 5.0, "dismiss": -4.0}
STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "have", "has", "had", "not", "but", "can", "will", "into", "using", "based",
    "via", "between", "through", "during", "after", "before", "about", "over",
}


@dataclass
class FeedContext:
    user_id: Optional[int]
    seed: int
    exclude_ids: Set[int] = field(default_factory=set)
    soft_exclude_ids: Set[int] = field(default_factory=set)
    interest_weights: Dict[str, float] = field(default_factory=dict)
    recent_papers: List[Paper] = field(default_factory=list)
    feed_shown: Set[int] = field(default_factory=set)
    refresh: bool = False


def load_topic_config() -> List[str]:
    path = os.path.join(os.path.dirname(__file__), "..", "crawler_config.json")
    try:
        with open(path, "r") as f:
            config = json.load(f)
        from utils.helpers import slugify_topic
        return [slugify_topic(t["name"]) for t in config.get("topics", [])]
    except Exception:
        return ["machine-learning", "deep-learning", "computer-vision"]


from utils.display import paper_abstract_snippet, format_topic


def paper_to_dict(paper: Paper, metrics: Optional[PaperMetrics] = None) -> dict:
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract_snippet": paper_abstract_snippet(paper),
        "published_date": paper.published_date.isoformat() if paper.published_date else None,
        "source_api": paper.source_api,
        "source_url": paper.source_url,
        "pdf_url": paper.pdf_url,
        "citation_count": paper.citation_count,
        "primary_topic": format_topic(paper.primary_topic),
        "primary_topic_slug": paper.primary_topic,
        "venue": paper.venue,
        "trending_score": metrics.trending_score if metrics else 0,
        "hybrid_impact": metrics.hybrid_impact if metrics else 0,
        "pdf_url": paper.pdf_url,
        "is_open_access": bool(getattr(paper, "is_open_access", False) or paper.pdf_url or paper.arxiv_id),
    }


def get_metrics_map(db: Session, paper_ids: List[int]) -> Dict[int, PaperMetrics]:
    if not paper_ids:
        return {}
    rows = db.query(PaperMetrics).filter(PaperMetrics.paper_id.in_(paper_ids)).all()
    return {m.paper_id: m for m in rows}


def variety_jitter(paper_id: int, seed: int, amplitude: float = 0.2) -> float:
    raw = hashlib.md5(f"{paper_id}:{seed}".encode()).hexdigest()
    return (int(raw[:8], 16) / 0xFFFFFFFF) * amplitude


def tokenize(text: str) -> Set[str]:
    if not text:
        return set()
    return {
        w.lower()
        for w in re.findall(r"\w+", text)
        if len(w) > 2 and w.lower() not in STOP_WORDS
    }


def content_affinity(paper: Paper, recent_papers: List[Paper]) -> float:
    if not recent_papers:
        return 0.0
    ptokens = tokenize(f"{paper.title or ''} {paper.abstract_snippet or ''}")
    if not ptokens:
        return 0.0
    sims = []
    for rp in recent_papers:
        rtokens = tokenize(f"{rp.title or ''} {rp.abstract_snippet or ''}")
        if not rtokens:
            continue
        union = ptokens | rtokens
        if union:
            sims.append(len(ptokens & rtokens) / len(union))
    return max(sims) if sims else 0.0


def user_topic_preferences(db: Session, user_id: Optional[int]) -> List[str]:
    if not user_id:
        return []
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    return pref.topic_slugs if pref and pref.topic_slugs else []


def user_interest_profile(
    db: Session, user_id: Optional[int], days: int = 30
) -> Tuple[Dict[str, float], List[Paper]]:
    """Build topic weights and recent papers from browsing behavior."""
    if not user_id:
        return {}, []

    cutoff = datetime.utcnow() - timedelta(days=days)
    events = (
        db.query(UserEvent)
        .filter(
            UserEvent.user_id == user_id,
            UserEvent.created_at >= cutoff,
            UserEvent.event_type.in_(["click", "view", "save", "dismiss"]),
        )
        .order_by(desc(UserEvent.created_at))
        .limit(250)
        .all()
    )

    topic_weights: Dict[str, float] = defaultdict(float)
    recent_paper_ids: List[int] = []
    paper_cache: Dict[int, Paper] = {}

    for i, ev in enumerate(events):
        decay = 1.0 / (1.0 + i * 0.04)
        weight = EVENT_WEIGHTS.get(ev.event_type, 0.0) * decay
        if weight == 0:
            continue

        paper = paper_cache.get(ev.paper_id)
        if paper is None:
            paper = db.query(Paper).filter(Paper.id == ev.paper_id).first()
            if paper:
                paper_cache[ev.paper_id] = paper
        if not paper:
            continue

        if ev.event_type in ("click", "view", "save") and ev.paper_id not in recent_paper_ids:
            recent_paper_ids.append(ev.paper_id)

        if paper.primary_topic:
            topic_weights[paper.primary_topic] += weight

        for t in db.query(PaperTopic).filter(PaperTopic.paper_id == paper.id).all():
            topic_weights[t.topic_slug] += weight * (t.confidence or 0.5)

    for slug in user_topic_preferences(db, user_id):
        topic_weights[slug] += 2.5

    recent_papers = [paper_cache[pid] for pid in recent_paper_ids[:25] if pid in paper_cache]
    return dict(topic_weights), recent_papers


def _load_feed_session(db: Session, user_id: Optional[int]) -> dict:
    cache = (
        db.query(FeedCache)
        .filter(FeedCache.row_id == SESSION_ROW_ID, FeedCache.user_id == user_id)
        .first()
    )
    if cache and isinstance(cache.paper_ids, dict):
        return cache.paper_ids
    if cache and isinstance(cache.paper_ids, list):
        return {"last_shown": cache.paper_ids, "prev_shown": [], "seed": 0}
    return {"last_shown": [], "prev_shown": [], "seed": 0}


def _save_feed_session(
    db: Session, user_id: Optional[int], seed: int, shown_ids: List[int]
) -> None:
    prev = _load_feed_session(db, user_id)
    payload = {
        "seed": seed,
        "last_shown": shown_ids,
        "prev_shown": (prev.get("last_shown") or [])[-120:],
        "updated_at": datetime.utcnow().isoformat(),
    }
    cache = (
        db.query(FeedCache)
        .filter(FeedCache.row_id == SESSION_ROW_ID, FeedCache.user_id == user_id)
        .first()
    )
    if cache:
        cache.paper_ids = payload
        cache.computed_at = datetime.utcnow()
    else:
        db.add(FeedCache(user_id=user_id, row_id=SESSION_ROW_ID, paper_ids=payload))
    db.commit()


def user_interacted_ids(db: Session, user_id: Optional[int]) -> Set[int]:
    if not user_id:
        return set()
    events = db.query(UserEvent.paper_id).filter(
        UserEvent.user_id == user_id,
        UserEvent.event_type.in_(["click", "save", "dismiss"])
    ).all()
    saved = db.query(SavedPaper.paper_id).filter(SavedPaper.user_id == user_id).all()
    return {r[0] for r in events} | {r[0] for r in saved}

def make_feed_context(
    db: Session,
    user_id: Optional[int],
    refresh: bool = False,
    client_seen_ids: Optional[Set[int]] = None,
) -> FeedContext:
    session = _load_feed_session(db, user_id)
    interest_weights, recent_papers = user_interest_profile(db, user_id)
    
    interacted = user_interacted_ids(db, user_id)
    client_seen = set(client_seen_ids or [])
    last_shown = set(session.get("last_shown") or [])
    prev_shown = set(session.get("prev_shown") or [])

    soft_exclude = client_seen | last_shown | prev_shown
    soft_exclude -= interacted

    if refresh:
        seed = int(time.time()) % 1_000_000_000
    else:
        event_factor = len(recent_papers) % 97
        client_factor = len(client_seen) % 53
        day_factor = datetime.utcnow().strftime("%Y%m%d")
        seed = int(
            hashlib.md5(
                f"{user_id}:{day_factor}:{event_factor}:{client_factor}".encode()
            ).hexdigest()[:8],
            16,
        )

    return FeedContext(
        user_id=user_id,
        seed=seed,
        exclude_ids=interacted,
        soft_exclude_ids=soft_exclude,
        interest_weights=interest_weights,
        recent_papers=recent_papers,
        refresh=refresh,
    )


def _ctx_for_row(ctx: FeedContext, row_id: str) -> FeedContext:
    """Per-row seed so refresh reshuffles every carousel, not only the hero."""
    row_seed = int(hashlib.md5(f"{ctx.seed}:{row_id}".encode()).hexdigest()[:8], 16)
    return FeedContext(
        user_id=ctx.user_id,
        seed=row_seed,
        exclude_ids=set(ctx.exclude_ids),
        soft_exclude_ids=set(ctx.soft_exclude_ids),
        interest_weights=ctx.interest_weights,
        recent_papers=ctx.recent_papers,
        feed_shown=ctx.feed_shown,
        refresh=ctx.refresh,
    )


def topic_interest_score(paper: Paper, ctx: FeedContext, db: Optional[Session] = None) -> float:
    if not ctx.interest_weights:
        return 0.0
    score = ctx.interest_weights.get(paper.primary_topic or "", 0.0)
    if score == 0.0 and db is not None:
        for t in db.query(PaperTopic).filter(PaperTopic.paper_id == paper.id).all():
            score = max(score, ctx.interest_weights.get(t.topic_slug, 0.0))
    return min(score / 10.0, 1.0)


def score_paper(
    paper: Paper,
    metrics: Optional[PaperMetrics],
    ctx: FeedContext,
    base: float,
    db: Optional[Session] = None,
) -> float:
    interest = topic_interest_score(paper, ctx, db)
    affinity = content_affinity(paper, ctx.recent_papers)
    emb_sim = 0.0
    paper_emb = get_paper_embedding(paper)
    if paper_emb and ctx.recent_papers:
        for rp in ctx.recent_papers[:8]:
            rp_emb = get_paper_embedding(rp)
            if rp_emb:
                emb_sim = max(emb_sim, cosine_similarity(paper_emb, rp_emb))

    open_access_boost = 0.12 if (getattr(paper, "is_open_access", False) or paper.pdf_url or paper.arxiv_id) else 0.0
    
    # On refresh, aggressively shuffle. Otherwise, gentle variety.
    jitter_amp = 1.5 if ctx.refresh else 0.2
    # Soft penalty (-0.4) pushes seen items down, but large refresh jitter (+1.5) can pull them back up
    soft_penalty = -0.4 if paper.id in ctx.soft_exclude_ids else 0.0

    return (
        base
        + 0.35 * interest
        + 0.30 * affinity
        + 0.20 * emb_sim
        + open_access_boost
        + soft_penalty
        + variety_jitter(paper.id, ctx.seed, jitter_amp)
    )


def _fallback_by_citations(db: Session, limit: int, ctx: Optional[FeedContext] = None) -> List[Paper]:
    pool = (
        db.query(Paper)
        .order_by(desc(Paper.citation_count), desc(Paper.published_date))
        .limit(limit * POOL_MULTIPLIER)
        .all()
    )
    if not ctx:
        return pool[:limit]
    return _select_from_query(
        db,
        db.query(Paper).order_by(desc(Paper.citation_count), desc(Paper.published_date)),
        ctx,
        limit,
        lambda p, m: min(p.citation_count / 5000.0, 1.0),
    )


def _fetch_with_soft_fallback(query, fallback_query, ctx: FeedContext, limit_mult: int) -> List[Paper]:
    hard_exclude = ctx.exclude_ids | ctx.feed_shown
    fully_unseen = hard_exclude | ctx.soft_exclude_ids
    
    candidates = []
    if fully_unseen:
        candidates = query.filter(Paper.id.notin_(fully_unseen)).limit(limit_mult).all()
        if not candidates and fallback_query is not None:
            candidates = fallback_query.filter(Paper.id.notin_(fully_unseen)).limit(limit_mult).all()
    else:
        candidates = query.limit(limit_mult).all()
        if not candidates and fallback_query is not None:
            candidates = fallback_query.limit(limit_mult).all()
            
    if len(candidates) < limit_mult // 2:
        if hard_exclude:
            backup = query.filter(Paper.id.notin_(hard_exclude)).limit(limit_mult).all()
            if not backup and fallback_query is not None:
                backup = fallback_query.filter(Paper.id.notin_(hard_exclude)).limit(limit_mult).all()
        else:
            backup = query.limit(limit_mult).all()
            if not backup and fallback_query is not None:
                backup = fallback_query.limit(limit_mult).all()
                
        seen_ids = {p.id for p in candidates}
        for p in backup:
            if p.id not in seen_ids:
                candidates.append(p)
                if len(candidates) >= limit_mult:
                    break
                    
    return candidates


def _select_from_query(
    db: Session,
    query,
    ctx: FeedContext,
    limit: int,
    base_scorer,
    max_per_topic: Optional[int] = None,
) -> List[Paper]:
    pool = _fetch_with_soft_fallback(query, None, ctx, limit * POOL_MULTIPLIER)

    if not pool:
        return []
    
    metrics_map = get_metrics_map(db, [p.id for p in pool])
    scored: List[Tuple[Paper, float]] = []

    for paper in pool:
        metrics = metrics_map.get(paper.id)
        base = base_scorer(paper, metrics)
        score = score_paper(paper, metrics, ctx, base, db)
        scored.append((paper, score))

    scored.sort(key=lambda x: -x[1])
    offset = (ctx.seed % max(1, len(scored) - limit + 1)) if len(scored) > limit else 0
    rotated = scored[offset:] + scored[:offset]
    return mmr_select(rotated, limit, max_per_topic=max_per_topic)


def mmr_select(
    candidates: List[Tuple[Paper, float]],
    limit: int,
    lambda_param: float = 0.72,
    max_per_topic: Optional[int] = None,
) -> List[Paper]:
    selected: List[Paper] = []
    selected_embeddings: List[List[float]] = []
    remaining = list(candidates)
    topic_counts: Dict[str, int] = {}
    topic_cap = max_per_topic if max_per_topic is not None else max(6, limit // 3)

    while remaining and len(selected) < limit:
        best_idx = 0
        best_score = -1.0
        for i, (paper, relevance) in enumerate(remaining):
            topic = paper.primary_topic or "unknown"
            if topic_counts.get(topic, 0) >= topic_cap:
                continue
            emb = get_paper_embedding(paper)
            if selected_embeddings and emb:
                max_sim = max(cosine_similarity(emb, se) for se in selected_embeddings if se)
                score = lambda_param * relevance - (1 - lambda_param) * max_sim
            else:
                score = relevance
            if score > best_score:
                best_score = score
                best_idx = i
        if best_score <= -1.0 and remaining:
            # Relax topic cap so rows still fill when catalog skews to one topic
            paper, _ = remaining.pop(0)
            selected.append(paper)
            continue
        if not remaining:
            break
        paper, _ = remaining.pop(best_idx)
        selected.append(paper)
        topic = paper.primary_topic or "unknown"
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        emb = get_paper_embedding(paper)
        if emb:
            selected_embeddings.append(emb)

    return selected


def trending_row(db: Session, limit: int = ROW_LIMIT, ctx: Optional[FeedContext] = None) -> List[Paper]:
    if ctx is None:
        ctx = FeedContext(user_id=None, seed=0)
    query = (
        db.query(Paper)
        .join(PaperMetrics, Paper.id == PaperMetrics.paper_id)
        .order_by(desc(PaperMetrics.trending_score))
    )
    papers = _select_from_query(
        db, query, ctx, limit,
        lambda p, m: min((m.trending_score / 10.0), 2.0) if m else 0.0,
    )
    return papers if papers else _fallback_by_citations(db, limit, ctx)


def high_impact_row(db: Session, limit: int = ROW_LIMIT, ctx: Optional[FeedContext] = None) -> List[Paper]:
    if ctx is None:
        ctx = FeedContext(user_id=None, seed=0)
    query = (
        db.query(Paper)
        .join(PaperMetrics, Paper.id == PaperMetrics.paper_id)
        .order_by(desc(PaperMetrics.hybrid_impact))
    )
    papers = _select_from_query(
        db, query, ctx, limit,
        lambda p, m: min((m.hybrid_impact / 10.0), 2.0) if m else 0.0,
    )
    return papers if papers else _fallback_by_citations(db, limit, ctx)


def topic_row(
    db: Session, topic_slug: str, limit: int = ROW_LIMIT, ctx: Optional[FeedContext] = None
) -> List[Paper]:
    if ctx is None:
        ctx = FeedContext(user_id=None, seed=0)
    query = (
        db.query(Paper)
        .join(PaperTopic, Paper.id == PaperTopic.paper_id)
        .filter(PaperTopic.topic_slug == topic_slug)
        .outerjoin(PaperMetrics, Paper.id == PaperMetrics.paper_id)
        .order_by(desc(PaperMetrics.trending_score), desc(Paper.citation_count))
    )
    papers = _select_from_query(
        db, query, ctx, limit,
        lambda p, m: min(((m.trending_score / 10.0) if m else 0.0) + 0.1, 2.0),
        max_per_topic=limit,
    )
    if papers:
        return papers
    fallback_query = (
        db.query(Paper)
        .filter(Paper.primary_topic == topic_slug)
        .order_by(desc(Paper.citation_count))
    )
    return _select_from_query(
        db, fallback_query, ctx, limit,
        lambda p, m: min(p.citation_count / 5000.0, 1.0),
        max_per_topic=limit,
    )


def user_seen_ids(db: Session, user_id: Optional[int]) -> Set[int]:
    if not user_id:
        return set()
    events = db.query(UserEvent.paper_id).filter(UserEvent.user_id == user_id).all()
    saved = db.query(SavedPaper.paper_id).filter(SavedPaper.user_id == user_id).all()
    return {r[0] for r in events} | {r[0] for r in saved}


def score_for_you(db: Session, user_id: Optional[int], paper: Paper, metrics: Optional[PaperMetrics], ctx: FeedContext) -> float:
    topic_match = topic_interest_score(paper, ctx, db)
    popularity = min((metrics.trending_score if metrics else 0.0) / 10.0, 1.0)
    recency = (metrics.recency_score if metrics else 0.0) / 10.0
    affinity = content_affinity(paper, ctx.recent_papers)

    content_sim = 0.0
    paper_emb = get_paper_embedding(paper)
    if paper_emb and ctx.recent_papers:
        for rp in ctx.recent_papers[:10]:
            rp_emb = get_paper_embedding(rp)
            if rp_emb:
                content_sim = max(content_sim, cosine_similarity(paper_emb, rp_emb))

    if user_id:
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if pref and pref.embedding_centroid and paper_emb:
            content_sim = max(content_sim, cosine_similarity(paper_emb, pref.embedding_centroid))

        dismissed = (
            db.query(UserEvent.paper_id)
            .filter(UserEvent.user_id == user_id, UserEvent.event_type == "dismiss")
            .all()
        )
        if dismissed and paper_emb:
            dismissed_papers = db.query(Paper).filter(Paper.id.in_([d[0] for d in dismissed])).all()
            for dp in dismissed_papers:
                dp_emb = get_paper_embedding(dp)
                if dp_emb and cosine_similarity(paper_emb, dp_emb) > 0.85:
                    return -1.0

    jitter_amp = 1.5 if ctx.refresh else 0.2
    soft_penalty = -0.4 if paper.id in ctx.soft_exclude_ids else 0.0

    return (
        0.30 * content_sim
        + 0.30 * topic_match
        + 0.25 * affinity
        + 0.10 * popularity
        + 0.05 * recency
        + soft_penalty
        + variety_jitter(paper.id, ctx.seed, jitter_amp)
    )


def for_you_row(
    db: Session, user_id: Optional[int], limit: int = ROW_LIMIT, ctx: Optional[FeedContext] = None
) -> List[Paper]:
    if ctx is None:
        ctx = FeedContext(user_id=user_id, seed=0)
    prefs = user_topic_preferences(db, user_id)
    top_topics = sorted(
        set(prefs) | set(ctx.interest_weights.keys()),
        key=lambda s: ctx.interest_weights.get(s, 0.0),
        reverse=True,
    )[:5]

    query = db.query(Paper).outerjoin(PaperMetrics, Paper.id == PaperMetrics.paper_id)
    if top_topics:
        query = query.join(PaperTopic, Paper.id == PaperTopic.paper_id).filter(
            PaperTopic.topic_slug.in_(top_topics)
        )

    fallback_query = db.query(Paper).outerjoin(PaperMetrics)
    candidates = _fetch_with_soft_fallback(query, fallback_query, ctx, limit * POOL_MULTIPLIER * 2)

    metrics_map = get_metrics_map(db, [p.id for p in candidates])
    scored: List[Tuple[Paper, float]] = []

    for paper in candidates:
        score = score_for_you(db, user_id, paper, metrics_map.get(paper.id), ctx)
        if score >= 0:
            scored.append((paper, score))

    scored.sort(key=lambda x: -x[1])
    if not scored:
        return _fallback_by_citations(db, limit, ctx)
    return mmr_select(scored, limit)


def because_you_read_row(
    db: Session, user_id: int, limit: int = ROW_LIMIT, ctx: Optional[FeedContext] = None
) -> List[Paper]:
    if ctx is None:
        ctx = FeedContext(user_id=user_id, seed=0)

    recent = (
        db.query(UserEvent)
        .filter(
            UserEvent.user_id == user_id,
            UserEvent.event_type.in_(["click", "view", "save"]),
        )
        .order_by(desc(UserEvent.created_at))
        .first()
    )
    if not recent:
        return []

    source = db.query(Paper).filter(Paper.id == recent.paper_id).first()
    if not source:
        return []

    source_emb = get_paper_embedding(source)

    if source_emb:
        candidates_query = db.query(Paper).filter(Paper.id != source.id)
        candidates = _fetch_with_soft_fallback(candidates_query, None, ctx, 300)

        scored = []
        for paper in candidates:
            emb = get_paper_embedding(paper)
            if emb:
                score = cosine_similarity(source_emb, emb) + variety_jitter(paper.id, ctx.seed)
                scored.append((paper, score))
        scored.sort(key=lambda x: -x[1])
        return [p for p, _ in scored[:limit]]

    same_topic = source.primary_topic or "machine-learning"
    return topic_row(db, same_topic, limit, ctx)


def ranked_topic_slugs(db: Session, user_id: Optional[int], ctx: FeedContext) -> List[str]:
    prefs = user_topic_preferences(db, user_id)
    config_topics = load_topic_config()
    candidates = list(dict.fromkeys(prefs + list(ctx.interest_weights.keys()) + config_topics))
    if not candidates:
        return config_topics[:3]
    if ctx.refresh:
        rng = random.Random(ctx.seed)
        rng.shuffle(candidates)
    else:
        candidates.sort(key=lambda s: ctx.interest_weights.get(s, 0.0), reverse=True)
    return candidates[:4]


def build_feed(
    db: Session,
    user_id: Optional[int] = None,
    refresh: bool = False,
    client_seen_ids: Optional[Set[int]] = None,
) -> dict:
    ctx = make_feed_context(
        db, user_id, refresh=refresh, client_seen_ids=client_seen_ids
    )
    rows: List[dict] = []
    all_shown: List[int] = []

    def add_row(row_id: str, title: str, papers: List[Paper]):
        if not papers:
            return
        metrics_map = get_metrics_map(db, [p.id for p in papers])
        rows.append({
            "id": row_id,
            "title": title,
            "papers": [paper_to_dict(p, metrics_map.get(p.id)) for p in papers],
        })
        for p in papers:
            all_shown.append(p.id)
            ctx.feed_shown.add(p.id)

    if ctx.recent_papers and user_id:
        because = because_you_read_row(db, user_id, ctx=_ctx_for_row(ctx, "because_you_read"))
        if because:
            add_row("because_you_read", "Because You Read", because)

    for_you = for_you_row(db, user_id, ctx=_ctx_for_row(ctx, "for_you"))
    add_row("for_you", "Recommended for You", for_you)

    trending = trending_row(db, ctx=_ctx_for_row(ctx, "trending"))
    add_row("trending", "Trending Now", trending)

    high_impact = high_impact_row(db, ctx=_ctx_for_row(ctx, "high_impact"))
    add_row("high_impact", "High Impact", high_impact)

    for slug in ranked_topic_slugs(db, user_id, ctx):
        papers = topic_row(db, slug, ctx=_ctx_for_row(ctx, f"topic_{slug}"))
        if papers:
            label = slug.replace("-", " ").title()
            add_row(f"topic_{slug}", label, papers)

    if user_id is not None:
        _save_feed_session(db, user_id, ctx.seed, all_shown)

    return {
        "rows": rows,
        "seed": ctx.seed,
        "personalized": bool(ctx.interest_weights or ctx.recent_papers),
        "refreshed": refresh,
        "shown_ids": all_shown,
    }


def similar_papers(db: Session, paper_id: int, limit: int = 10) -> List[Paper]:
    source = db.query(Paper).filter(Paper.id == paper_id).first()
    if not source:
        return []
    source_emb = get_paper_embedding(source)
    if not source_emb:
        return topic_row(db, source.primary_topic or "machine-learning", limit)

    candidates = db.query(Paper).filter(Paper.id != paper_id).limit(300).all()
    scored = []
    for paper in candidates:
        emb = get_paper_embedding(paper)
        if emb:
            scored.append((paper, cosine_similarity(source_emb, emb)))
    scored.sort(key=lambda x: -x[1])
    return [p for p, _ in scored[:limit]]
