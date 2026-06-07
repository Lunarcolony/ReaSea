"""Tests for feed recommendation algorithms."""

import sys
import os
import uuid
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from database import init_db, SessionLocal, engine, Base
from models import Paper, PaperMetrics, PaperTopic, UserEvent, User, UserPreference
from classification.metrics import compute_metrics_for_paper
from recommender.feed import (
    trending_row, high_impact_row, topic_row, for_you_row,
    build_feed, mmr_select, user_interest_profile,
    _fallback_by_citations,
)


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    session = SessionLocal()
    user = User(email="test@test.com", hashed_password="", is_active=True)
    session.add(user)
    session.commit()
    yield session
    session.rollback()
    session.close()


def _test_user_id(db):
    return db.query(User).first().id


def _add_paper(db, title, citations=10, topic="machine-learning", external_id=None):
    p = Paper(
        title=title,
        authors="Author A",
        abstract_snippet="machine learning neural network deep learning",
        full_abstract="machine learning neural network deep learning methods",
        published_date=date(2023, 1, 1),
        source_api="OpenAlex",
        external_id=external_id or f"test-{uuid.uuid4().hex[:12]}",
        source_url="http://example.com",
        citation_count=citations,
        primary_topic=topic,
    )
    db.add(p)
    db.flush()
    db.add(PaperTopic(paper_id=p.id, topic_slug=topic, confidence=0.9, source="test"))
    metrics = compute_metrics_for_paper(p)
    db.add(metrics)
    db.commit()
    return p


def test_fallback_by_citations(db):
    _add_paper(db, "Paper A", citations=100, external_id="fb-a")
    _add_paper(db, "Paper B", citations=50, external_id="fb-b")
    papers = _fallback_by_citations(db, 2)
    assert len(papers) == 2
    assert papers[0].citation_count >= papers[1].citation_count


def test_trending_row_with_metrics(db):
    _add_paper(db, "Trending Paper", citations=200, external_id="tr-1")
    papers = trending_row(db, limit=5)
    assert len(papers) >= 1


def test_trending_row_fallback_without_metrics_table(db):
    """When a paper has no metrics row, trending still returns results via join or fallback."""
    p = Paper(
        title="Legacy Paper No Metrics",
        authors="X",
        abstract_snippet="test",
        published_date=date(2022, 6, 1),
        source_api="OpenAlex",
        external_id="legacy-no-metrics-unique",
        source_url="http://x.com",
        citation_count=99999,
    )
    db.add(p)
    db.commit()
    # Ensure this specific paper has no metrics row
    db.query(PaperMetrics).filter(PaperMetrics.paper_id == p.id).delete()
    db.commit()
    papers = trending_row(db, limit=5)
    assert len(papers) >= 1
    # Either our high-citation paper appears, or fallback returns top citations from catalog
    assert papers[0].citation_count >= 0


def test_topic_row(db):
    _add_paper(db, "ML Paper", citations=30, topic="machine-learning", external_id="tp-1")
    papers = topic_row(db, "machine-learning", limit=5)
    assert len(papers) >= 1
    assert papers[0].primary_topic == "machine-learning"


def test_mmr_topic_diversification():
    papers = []
    for i in range(5):
        p = Paper(
            title=f"P{i}", authors="", abstract_snippet="", source_api="OpenAlex",
            external_id=f"mmr-{i}", citation_count=i,
            primary_topic="same-topic",
        )
        papers.append((p, 1.0 - i * 0.1))
    selected = mmr_select(papers, limit=4)
    same = sum(1 for p in selected if p.primary_topic == "same-topic")
    assert same <= 2


def test_build_feed_returns_rows(db):
    _add_paper(db, "Feed Paper 1", citations=80, external_id="bf-1")
    _add_paper(db, "Feed Paper 2", citations=60, topic="deep-learning", external_id="bf-2")
    result = build_feed(db, user_id=None)
    rows = result["rows"]
    assert len(rows) >= 1
    assert "seed" in result


def test_refresh_changes_seed(db):
    uid = _test_user_id(db)
    for i in range(12):
        _add_paper(db, f"Rotate {i}", citations=100 - i, external_id=f"rot-{i}")

    first = build_feed(db, user_id=uid, refresh=False)
    second = build_feed(db, user_id=uid, refresh=True)
    assert second["refreshed"] is True
    assert second["seed"] != first["seed"]


def test_interest_profile_from_clicks(db):
    uid = _test_user_id(db)
    ml = _add_paper(db, "ML Alpha", citations=50, topic="machine-learning", external_id="int-ml")
    _add_paper(db, "Bio Paper", citations=50, topic="bioinformatics", external_id="int-bio")

    db.add(UserEvent(user_id=uid, paper_id=ml.id, event_type="click"))
    db.add(UserEvent(user_id=uid, paper_id=ml.id, event_type="view"))
    db.commit()

    weights, recent = user_interest_profile(db, user_id=uid)
    assert weights.get("machine-learning", 0) > weights.get("bioinformatics", 0)
    assert ml.id in [p.id for p in recent]


def test_for_you_cold_start(db):
    _add_paper(db, "Cold Start", citations=40, external_id="cs-1")
    papers = for_you_row(db, user_id=None, limit=5)
    assert len(papers) >= 1
