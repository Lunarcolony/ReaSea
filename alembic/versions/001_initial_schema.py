"""Initial extended schema

Revision ID: 001
Revises:
Create Date: 2026-06-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("authors", sa.String(), nullable=True),
        sa.Column("abstract_snippet", sa.Text(), nullable=True),
        sa.Column("full_abstract", sa.Text(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("source_api", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("doi", sa.String(), nullable=True),
        sa.Column("pdf_url", sa.String(), nullable=True),
        sa.Column("venue", sa.String(), nullable=True),
        sa.Column("publication_type", sa.String(), nullable=True),
        sa.Column("openalex_id", sa.String(), nullable=True),
        sa.Column("arxiv_id", sa.String(), nullable=True),
        sa.Column("pmid", sa.String(), nullable=True),
        sa.Column("primary_topic", sa.String(), nullable=True),
        sa.Column("concepts_json", sa.JSON(), nullable=True),
        sa.Column("fields_of_study", sa.JSON(), nullable=True),
        sa.Column("ingestion_topic", sa.String(), nullable=True),
        sa.Column("embedding_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_papers_id", "papers", ["id"])
    op.create_index("ix_papers_title", "papers", ["title"])
    op.create_index("ix_papers_published_date", "papers", ["published_date"])
    op.create_index("ix_papers_source_api", "papers", ["source_api"])
    op.create_index("ix_papers_external_id", "papers", ["external_id"])
    op.create_index("ix_papers_doi", "papers", ["doi"])
    op.create_index("ix_papers_openalex_id", "papers", ["openalex_id"])
    op.create_index("ix_papers_arxiv_id", "papers", ["arxiv_id"])
    op.create_index("ix_papers_pmid", "papers", ["pmid"])
    op.create_index("ix_papers_primary_topic", "papers", ["primary_topic"])
    op.create_index("ix_papers_ingestion_topic", "papers", ["ingestion_topic"])

    op.create_table(
        "crawler_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("crawler_name", sa.String(), nullable=False),
        sa.Column("topic_name", sa.String(), nullable=False),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("last_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawler_states_crawler_name", "crawler_states", ["crawler_name"])
    op.create_index("ix_crawler_states_topic_name", "crawler_states", ["topic_name"])

    op.create_table(
        "authors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("openalex_id", sa.String(), nullable=True),
        sa.Column("h_index", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("openalex_id"),
    )
    op.create_index("ix_authors_name", "authors", ["name"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("research_role", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "paper_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("topic_slug", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True, server_default="1.0"),
        sa.Column("source", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("paper_id", "topic_slug", name="uq_paper_topic"),
    )
    op.create_index("ix_paper_topics_paper_id", "paper_topics", ["paper_id"])
    op.create_index("ix_paper_topics_topic_slug", "paper_topics", ["topic_slug"])

    op.create_table(
        "paper_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("hybrid_impact", sa.Float(), nullable=True, server_default="0"),
        sa.Column("citation_velocity", sa.Float(), nullable=True, server_default="0"),
        sa.Column("recency_score", sa.Float(), nullable=True, server_default="0"),
        sa.Column("venue_tier", sa.Float(), nullable=True, server_default="0.5"),
        sa.Column("engagement_score", sa.Float(), nullable=True, server_default="0"),
        sa.Column("trending_score", sa.Float(), nullable=True, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("paper_id"),
    )
    op.create_index("ix_paper_metrics_paper_id", "paper_metrics", ["paper_id"])
    op.create_index("ix_paper_metrics_trending_score", "paper_metrics", ["trending_score"])

    op.create_table(
        "paper_authors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True, server_default="0"),
        sa.ForeignKeyConstraint(["author_id"], ["authors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("paper_id", "author_id", name="uq_paper_author"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_slugs", sa.JSON(), nullable=True),
        sa.Column("embedding_centroid", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "user_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("read_time_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_events_user_id", "user_events", ["user_id"])
    op.create_index("ix_user_events_paper_id", "user_events", ["paper_id"])
    op.create_index("ix_user_events_user_paper", "user_events", ["user_id", "paper_id"])

    op.create_table(
        "saved_papers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "paper_id", name="uq_saved_paper"),
    )

    op.create_table(
        "feed_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("row_id", sa.String(), nullable=False),
        sa.Column("paper_ids", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "row_id", name="uq_feed_cache"),
    )
    op.create_index("ix_feed_cache_row_id", "feed_cache", ["row_id"])

    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_runs_job_name", "job_runs", ["job_name"])


def downgrade() -> None:
    for table in [
        "job_runs", "feed_cache", "saved_papers", "user_events", "user_preferences",
        "paper_authors", "paper_metrics", "paper_topics", "users", "authors",
        "crawler_states", "papers",
    ]:
        op.drop_table(table)
