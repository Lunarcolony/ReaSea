import os
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Float, Boolean,
    ForeignKey, UniqueConstraint, Index, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# pgvector support when using PostgreSQL
USE_PGVECTOR = os.getenv("DATABASE_URL", "").startswith("postgresql")
if USE_PGVECTOR:
    try:
        from pgvector.sqlalchemy import Vector
    except ImportError:
        USE_PGVECTOR = False


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    authors = Column(String, nullable=True)
    abstract_snippet = Column(Text, nullable=True)
    full_abstract = Column(Text, nullable=True)
    published_date = Column(Date, nullable=True, index=True)
    source_api = Column(String, index=True, nullable=False)
    external_id = Column(String, unique=True, index=True, nullable=False)
    source_url = Column(String, nullable=True)
    citation_count = Column(Integer, default=0, nullable=False)
    doi = Column(String, nullable=True, index=True)
    pdf_url = Column(String, nullable=True)
    venue = Column(String, nullable=True)
    publication_type = Column(String, nullable=True)
    openalex_id = Column(String, nullable=True, index=True)
    arxiv_id = Column(String, nullable=True, index=True)
    pmid = Column(String, nullable=True, index=True)
    primary_topic = Column(String, nullable=True, index=True)
    concepts_json = Column(JSON, nullable=True)
    fields_of_study = Column(JSON, nullable=True)
    ingestion_topic = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    topics = relationship("PaperTopic", back_populates="paper", cascade="all, delete-orphan")
    metrics = relationship("PaperMetrics", back_populates="paper", uselist=False, cascade="all, delete-orphan")
    paper_authors = relationship("PaperAuthor", back_populates="paper", cascade="all, delete-orphan")
    saved_by = relationship("SavedPaper", back_populates="paper", cascade="all, delete-orphan")

    if USE_PGVECTOR:
        embedding = Column(Vector(384), nullable=True)
    else:
        embedding_json = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Paper(title='{self.title[:30]}...', source='{self.source_api}')>"


class CrawlerState(Base):
    __tablename__ = "crawler_states"

    id = Column(Integer, primary_key=True, index=True)
    crawler_name = Column(String, index=True, nullable=False)
    topic_name = Column(String, index=True, nullable=False)
    query = Column(String, nullable=False)
    last_offset = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PaperTopic(Base):
    __tablename__ = "paper_topics"
    __table_args__ = (UniqueConstraint("paper_id", "topic_slug", name="uq_paper_topic"),)

    id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_slug = Column(String, nullable=False, index=True)
    confidence = Column(Float, default=1.0)
    source = Column(String, nullable=False)  # crawler | classifier | openalex

    paper = relationship("Paper", back_populates="topics")


class PaperMetrics(Base):
    __tablename__ = "paper_metrics"

    id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    hybrid_impact = Column(Float, default=0.0)
    citation_velocity = Column(Float, default=0.0)
    recency_score = Column(Float, default=0.0)
    venue_tier = Column(Float, default=0.5)
    engagement_score = Column(Float, default=0.0)
    trending_score = Column(Float, default=0.0, index=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    paper = relationship("Paper", back_populates="metrics")


class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    openalex_id = Column(String, nullable=True, unique=True)
    h_index = Column(Integer, nullable=True)

    paper_authors = relationship("PaperAuthor", back_populates="author")


class PaperAuthor(Base):
    __tablename__ = "paper_authors"
    __table_args__ = (UniqueConstraint("paper_id", "author_id", name="uq_paper_author"),)

    id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, default=0)

    paper = relationship("Paper", back_populates="paper_authors")
    author = relationship("Author", back_populates="paper_authors")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    research_role = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    events = relationship("UserEvent", back_populates="user", cascade="all, delete-orphan")
    saved_papers = relationship("SavedPaper", back_populates="user", cascade="all, delete-orphan")
    feed_caches = relationship("FeedCache", back_populates="user", cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    topic_slugs = Column(JSON, default=list)
    embedding_centroid = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="preferences")


class UserEvent(Base):
    __tablename__ = "user_events"
    __table_args__ = (Index("ix_user_events_user_paper", "user_id", "paper_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # view, click, save, dismiss
    read_time_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="events")


class SavedPaper(Base):
    __tablename__ = "saved_papers"
    __table_args__ = (UniqueConstraint("user_id", "paper_id", name="uq_saved_paper"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="saved_papers")
    paper = relationship("Paper", back_populates="saved_by")


class FeedCache(Base):
    __tablename__ = "feed_cache"
    __table_args__ = (UniqueConstraint("user_id", "row_id", name="uq_feed_cache"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    row_id = Column(String, nullable=False, index=True)
    paper_ids = Column(JSON, default=list)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="feed_caches")


class JobRun(Base):
    __tablename__ = "job_runs"

    id = Column(Integer, primary_key=True)
    job_name = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)  # running, success, failed
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    details = Column(JSON, nullable=True)
