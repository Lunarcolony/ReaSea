"""Tests for crawlers, metrics, and classification."""

import pytest
from datetime import date

from utils.helpers import slugify_topic, paper_fields_for_db
from classification.topics import classify_paper_topics
from classification.metrics import compute_metrics_for_paper, venue_tier
from models import Paper


def test_slugify_topic():
    assert slugify_topic("Machine Learning") == "machine-learning"
    assert slugify_topic("AI & Robotics") == "ai-robotics"


def test_venue_tier():
    assert venue_tier("Nature Communications") == 1.0
    assert venue_tier("Random Journal") == 0.5


def test_compute_metrics():
    paper = Paper(
        title="Test",
        source_api="OpenAlex",
        external_id="test-1",
        citation_count=100,
        published_date=date(2020, 1, 1),
        venue="NeurIPS",
    )
    paper.id = 1
    metrics = compute_metrics_for_paper(paper)
    assert metrics.citation_velocity > 0
    assert metrics.trending_score > 0
    assert metrics.venue_tier == 0.9


def test_classify_paper_topics():
    paper = Paper(
        title="Deep Learning for Computer Vision",
        source_api="OpenAlex",
        external_id="test-2",
        full_abstract="We propose a neural network for image recognition using deep learning.",
        ingestion_topic="deep-learning",
    )
    paper.id = 2
    topics = classify_paper_topics(paper)
    slugs = [t[0] for t in topics]
    assert "deep-learning" in slugs or "computer-vision" in slugs


def test_paper_fields_for_db_filters():
    data = {
        "title": "Test",
        "authors": "A",
        "abstract_snippet": "abs",
        "published_date": date.today(),
        "source_api": "OpenAlex",
        "external_id": "x1",
        "source_url": "http://x",
        "citation_count": 1,
        "hybrid_score": 99.9,
        "invalid_key": "drop me",
    }
    filtered = paper_fields_for_db(data)
    assert "hybrid_score" not in filtered
    assert "invalid_key" not in filtered
    assert filtered["title"] == "Test"
