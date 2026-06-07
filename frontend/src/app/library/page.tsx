"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PaperCard } from "@/components/PaperCard";
import type { Paper } from "@/lib/api";

export default function LibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.readingList().then((data) => setPapers(data.papers || [])).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading library...</div>;

  return (
    <div className="page library-page">
      <div className="page-header">
        <h1>My Library</h1>
        <p className="page-subtitle">Papers you&apos;ve saved to read later.</p>
      </div>
      {papers.length === 0 ? (
        <div className="empty-state empty-state--inline">
          <p>No saved papers yet.</p>
          <p className="page-subtitle">Browse the feed and tap Save on papers you want to keep.</p>
        </div>
      ) : (
        <div className="library-grid">
          {papers.map((p) => (
            <PaperCard key={p.id} paper={p} variant="grid" />
          ))}
        </div>
      )}
    </div>
  );
}
