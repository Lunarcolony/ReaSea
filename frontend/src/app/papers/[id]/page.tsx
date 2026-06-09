"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, Paper } from "@/lib/api";
import { isPaperSaved, toggleSavedPaper } from "@/lib/savedPapers";
import { PaperCard } from "@/components/PaperCard";
import { paperAbstract, formatAuthors, formatDate, formatCitations } from "@/lib/format";

export default function PaperDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [paper, setPaper] = useState<Paper | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api
      .getPaper(id)
      .then((data) => setPaper({ ...data, saved: isPaperSaved(data.id) }))
      .finally(() => setLoading(false));
    api.recordEvent(id, "view").catch(() => {});
  }, [id]);

  const handleSave = async () => {
    if (!paper) return;
    const saved = toggleSavedPaper(paper);
    setPaper({ ...paper, saved });
  };

  if (loading) return <div className="loading">Loading paper...</div>;
  if (!paper) return <div className="error-state"><h2>Paper not found</h2></div>;

  const abstract = paper.full_abstract || paperAbstract(paper);

  return (
    <article className="page paper-detail">
      <div className="detail-header">
        <span className="source-badge">{paper.source_api}</span>
        {paper.primary_topic && <span className="topic-tag">{paper.primary_topic}</span>}
        {paper.venue && <span className="venue-tag">{paper.venue}</span>}
      </div>
      <h1>{paper.title}</h1>
      <p className="authors">{formatAuthors(paper.authors, 500)}</p>
      <div className="metrics">
        {paper.published_date && <span>{formatDate(paper.published_date)}</span>}
        <span>{formatCitations(paper.citation_count)}</span>
        {paper.trending_score != null && paper.trending_score > 0 && (
          <span className="metric-pill">Trending {paper.trending_score.toFixed(1)}</span>
        )}
      </div>
      <section className="abstract-section">
        <h2>Abstract</h2>
        <p className="full-abstract">{abstract}</p>
      </section>
      <div className="detail-actions">
        <button type="button" className="btn primary" onClick={handleSave}>
          {paper.saved ? "Remove from Library" : "Save to Library"}
        </button>
        {paper.pdf_url && (
          <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer" className="btn secondary">
            Open PDF
          </a>
        )}
        {paper.source_url && (
          <a href={paper.source_url} target="_blank" rel="noopener noreferrer" className="btn secondary">
            View Source
          </a>
        )}
      </div>
      {paper.similar && paper.similar.length > 0 && (
        <section className="similar">
          <h2>Similar Papers</h2>
          <div className="similar-grid">
            {paper.similar.map((p) => (
              <PaperCard key={p.id} paper={p} variant="grid" />
            ))}
          </div>
        </section>
      )}
    </article>
  );
}
