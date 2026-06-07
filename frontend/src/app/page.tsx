"use client";

import { useCallback, useEffect, useState } from "react";
import { api, FeedRow } from "@/lib/api";
import { FeedRowSection } from "@/components/FeedRow";
import { HeroBanner } from "@/components/HeroBanner";
import { FeedSkeleton } from "@/components/FeedSkeleton";

export default function HomePage() {
  const [rows, setRows] = useState<FeedRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [personalized, setPersonalized] = useState(false);

  const loadFeed = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const data = await api.getFeed(refresh);
      setRows(data.rows || []);
      setPersonalized(Boolean(data.personalized));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load feed");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadFeed(false);
  }, [loadFeed]);

  const heroPaper =
    rows.find((r) => r.id === "for_you")?.papers?.[0] ||
    rows.find((r) => r.id === "because_you_read")?.papers?.[0] ||
    rows.find((r) => r.id === "trending")?.papers?.[0];

  const handleSave = useCallback(async (id: number) => {
    await api.savePaper(id);
    api.recordEvent(id, "save").catch(() => {});
    setRows((prev) =>
      prev.map((row) => ({
        ...row,
        papers: row.papers.map((p) => (p.id === id ? { ...p, saved: true } : p)),
      }))
    );
  }, []);

  const handleRefresh = () => loadFeed(true);

  if (loading) return <FeedSkeleton />;
  if (error)
    return (
      <div className="error-state">
        <h2>Could not load feed</h2>
        <p>{error}</p>
        <p className="error-state__hint">Make sure the API is running on port 8000.</p>
        <button type="button" className="btn primary" onClick={() => loadFeed(false)}>
          Try again
        </button>
      </div>
    );

  if (!rows.length)
    return (
      <div className="empty-state">
        <h2>No papers yet</h2>
        <p>Run the crawler to populate your research catalog.</p>
      </div>
    );

  return (
    <div className="home">
      <div className="feed-toolbar">
        <div className="feed-toolbar__text">
          <h1 className="feed-toolbar__title">Your feed</h1>
          <p className="feed-toolbar__subtitle">
            {personalized
              ? "Personalized from your topics and reading activity"
              : "Explore papers — click any card to teach the feed your interests"}
          </p>
        </div>
        <button
          type="button"
          className="btn secondary feed-refresh-btn"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh feed"}
        </button>
      </div>
      {heroPaper && <HeroBanner paper={heroPaper} />}
      {rows.map((row) => (
        <FeedRowSection key={row.id} row={row} onSave={handleSave} />
      ))}
    </div>
  );
}
