"use client";

import { useCallback, useEffect, useState } from "react";
import { api, FeedRow, Paper } from "@/lib/api";
import { getSeenPaperIds, recordShownPaperIds, clearSeenPaperIds } from "@/lib/seenPapers";
import { applySavedState, toggleSavedPaper } from "@/lib/savedPapers";
import { FeedRowSection } from "@/components/FeedRow";
import { FeedYouTubeView } from "@/components/FeedYouTubeView";
import { FeedControls } from "@/components/FeedControls";
import { HeroBanner } from "@/components/HeroBanner";
import { FeedSkeleton } from "@/components/FeedSkeleton";
import { FeedViewId, ThemeId, getFeedView, getTheme } from "@/lib/preferences";

export default function HomePage() {
  const [rows, setRows] = useState<FeedRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [personalized, setPersonalized] = useState(false);
  const [theme, setThemeState] = useState<ThemeId>("dark");
  const [view, setViewState] = useState<FeedViewId>("carousel");

  useEffect(() => {
    setThemeState(getTheme());
    setViewState(getFeedView());
  }, []);

  const loadFeed = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const seenIds = getSeenPaperIds();
      const data = await api.getFeed(refresh, seenIds);
      const nextRows =
        data.rows?.map((row: FeedRow) => ({
          ...row,
          papers: applySavedState(row.papers),
        })) || [];
      setRows(nextRows);
      setPersonalized(Boolean(data.personalized));
      const shown =
        data.shown_ids ||
        (data.rows || []).flatMap((row: FeedRow) => row.papers.map((p) => p.id));
      recordShownPaperIds(shown);
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

  const handleSave = useCallback((id: number) => {
    setRows((prev) => {
      let toggled = false;
      const next = prev.map((row) => ({
        ...row,
        papers: row.papers.map((p) => {
          if (p.id !== id || toggled) return p;
          toggled = true;
          const saved = toggleSavedPaper(p as Paper);
          return { ...p, saved };
        }),
      }));
      return next;
    });
  }, []);

  const handlePaperClick = useCallback((id: number) => {
    api.recordEvent(id, "click").catch(() => {});
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

  if (!rows.length) {
    const seenCount = getSeenPaperIds().length;
    return (
      <div className="empty-state">
        <h2>You're all caught up!</h2>
        <p>
          You've explored all the fresh papers currently in your catalog (you've seen {seenCount} papers).
        </p>
        <p>Leave the crawler running to find more, or clear your history to explore the existing ones again.</p>
        <div style={{ marginTop: "1rem" }}>
          <button
            type="button"
            className="btn secondary"
            onClick={() => {
              clearSeenPaperIds();
              window.location.reload();
            }}
          >
            Clear read history & start over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="home">
      <div className="feed-toolbar">
        <div className="feed-toolbar__text">
          <h1 className="feed-toolbar__title">Your feed</h1>
          <p className="feed-toolbar__subtitle">
            {personalized
              ? "Personalized from your topics and reading activity"
              : "Explore open-access papers — click any card to teach the feed your interests"}
          </p>
        </div>
        <div className="feed-toolbar__actions">
          <FeedControls
            theme={theme}
            view={view}
            onThemeChange={setThemeState}
            onViewChange={setViewState}
          />
          <button
            type="button"
            className="btn secondary feed-refresh-btn"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing…" : "Refresh feed"}
          </button>
        </div>
      </div>
      {view === "carousel" && heroPaper && <HeroBanner paper={heroPaper} />}
      {view === "carousel" ? (
        rows.map((row) => <FeedRowSection key={row.id} row={row} onSave={handleSave} />)
      ) : (
        <FeedYouTubeView rows={rows} onSave={handleSave} onPaperClick={handlePaperClick} />
      )}
    </div>
  );
}
