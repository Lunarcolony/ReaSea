"use client";

import type { FeedRow } from "@/lib/api";
import { PaperCard } from "./PaperCard";

interface FeedYouTubeViewProps {
  rows: FeedRow[];
  onSave?: (id: number) => void;
  onPaperClick?: (id: number) => void;
}

export function FeedYouTubeView({ rows, onSave, onPaperClick }: FeedYouTubeViewProps) {
  return (
    <div className="youtube-feed">
      {rows.map((row) => (
        <section key={row.id} className="youtube-feed__section">
          <h2 className="youtube-feed__title">{row.title}</h2>
          <div className="youtube-grid">
            {row.papers.map((paper) => (
              <PaperCard
                key={paper.id}
                paper={paper}
                onSave={onSave}
                onClick={onPaperClick}
                variant="youtube"
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
