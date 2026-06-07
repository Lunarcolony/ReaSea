"use client";

import type { Paper } from "@/lib/api";
import { api } from "@/lib/api";
import Link from "next/link";
import { paperAbstract, formatAuthors, formatCitations } from "@/lib/format";

interface HeroBannerProps {
  paper: Paper;
}

export function HeroBanner({ paper }: HeroBannerProps) {
  const abstract = paperAbstract(paper);

  const handleClick = () => {
    api.recordEvent(paper.id, "click").catch(() => {});
  };

  return (
    <section className="hero">
      <div className="hero__glow" aria-hidden />
      <div className="hero-content">
        <div className="hero__badges">
          <span className="hero-label">Featured Research</span>
          <span className="source-badge">{paper.source_api}</span>
          {paper.citation_count > 0 && (
            <span className="citation-badge">{formatCitations(paper.citation_count)}</span>
          )}
        </div>
        <h1>{paper.title}</h1>
        <p className="hero-authors">{formatAuthors(paper.authors, 120)}</p>
        <p className="hero-abstract">{abstract}</p>
        <div className="hero-actions">
          <Link href={`/papers/${paper.id}`} className="btn primary" onClick={handleClick}>
            Read summary
          </Link>
          {paper.pdf_url && (
            <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer" className="btn secondary">
              Open PDF
            </a>
          )}
          {paper.source_url && (
            <a href={paper.source_url} target="_blank" rel="noopener noreferrer" className="btn secondary">
              Source
            </a>
          )}
        </div>
      </div>
    </section>
  );
}
