"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PaperCard } from "@/components/PaperCard";
import type { Paper } from "@/lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const runSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setPapers([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    try {
      const data = await api.search(q);
      setPapers(data.papers || []);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => runSearch(query), 350);
    return () => clearTimeout(t);
  }, [query, runSearch]);

  return (
    <div className="page search-page">
      <div className="page-header">
        <h1>Search Papers</h1>
        <p className="page-subtitle">Find research by title, author, or topic.</p>
      </div>
      <div className="search-bar-wrap">
        <span className="search-icon" aria-hidden>
          ⌕
        </span>
        <input
          type="search"
          placeholder="Try machine learning, transformers, bioinformatics..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="search-input"
          autoFocus
        />
      </div>
      {loading && <p className="status-text">Searching...</p>}
      {!loading && searched && papers.length === 0 && (
        <div className="empty-state empty-state--inline">
          <p>No results for &ldquo;{query}&rdquo;</p>
        </div>
      )}
      {!loading && papers.length > 0 && (
        <p className="results-count">{papers.length} result{papers.length === 1 ? "" : "s"}</p>
      )}
      <div className="search-results">
        {papers.map((p) => (
          <PaperCard key={p.id} paper={p} variant="grid" />
        ))}
      </div>
    </div>
  );
}
