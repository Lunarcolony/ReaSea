"use client";

import type { Paper } from "@/lib/api";
import Link from "next/link";
import { paperAbstract, formatAuthors, formatDate, formatCitations } from "@/lib/format";

interface PaperCardProps {
  paper: Paper;
  onSave?: (id: number) => void;
  onClick?: (id: number) => void;
  variant?: "feed" | "grid" | "youtube";
}

export function PaperCard({ paper, onSave, onClick, variant = "feed" }: PaperCardProps) {
  const abstract = paperAbstract(paper);
  const isPlaceholder = abstract.startsWith("Abstract not available");

  return (
    <article className={`paper-card paper-card--${variant}`}>
      {variant === "youtube" && (
        <div className="paper-card__thumb" aria-hidden>
          <span className="paper-card__thumb-topic">{paper.primary_topic || "Research"}</span>
          {(paper.is_open_access || paper.pdf_url) && (
            <span className="paper-card__free-badge">Free PDF</span>
          )}
        </div>
      )}
      <Link
        href={`/papers/${paper.id}`}
        className="paper-card__link"
        onClick={() => onClick?.(paper.id)}
      >
        <div className="card-top">
          <span className="source-badge">{paper.source_api}</span>
          {paper.citation_count > 0 && (
            <span className="citation-badge">{formatCitations(paper.citation_count)}</span>
          )}
          {(paper.is_open_access || paper.pdf_url) && variant !== "youtube" && (
            <span className="free-badge">Free</span>
          )}
        </div>
        <h3 className="paper-card__title">{paper.title}</h3>
        <p className="authors">{formatAuthors(paper.authors)}</p>
        <p className={`abstract ${isPlaceholder ? "abstract--muted" : ""}`}>{abstract}</p>
      </Link>
      <div className="card-footer">
        <div className="card-footer__meta">
          {paper.primary_topic && <span className="topic-tag">{paper.primary_topic}</span>}
          {paper.published_date && <span className="date">{formatDate(paper.published_date)}</span>}
        </div>
        {onSave && (
          <button
            type="button"
            className={`save-btn ${paper.saved ? "save-btn--saved" : ""}`}
            onClick={() => onSave(paper.id)}
            aria-label={paper.saved ? "Remove from library" : "Save to library"}
          >
            {paper.saved ? "Saved" : "Save"}
          </button>
        )}
      </div>
    </article>
  );
}
