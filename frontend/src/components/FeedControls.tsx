"use client";

import { FeedViewId, ThemeId, FEED_VIEWS, THEMES, setFeedView, setTheme } from "@/lib/preferences";

interface FeedControlsProps {
  theme: ThemeId;
  view: FeedViewId;
  onThemeChange: (theme: ThemeId) => void;
  onViewChange: (view: FeedViewId) => void;
}

export function FeedControls({ theme, view, onThemeChange, onViewChange }: FeedControlsProps) {
  return (
    <div className="feed-controls">
      <label className="feed-controls__group">
        <span className="feed-controls__label">Theme</span>
        <select
          className="feed-controls__select"
          value={theme}
          onChange={(e) => {
            const next = e.target.value as ThemeId;
            setTheme(next);
            onThemeChange(next);
          }}
        >
          {THEMES.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </select>
      </label>
      <label className="feed-controls__group">
        <span className="feed-controls__label">View</span>
        <select
          className="feed-controls__select"
          value={view}
          onChange={(e) => {
            const next = e.target.value as FeedViewId;
            setFeedView(next);
            onViewChange(next);
          }}
        >
          {FEED_VIEWS.map((v) => (
            <option key={v.id} value={v.id}>
              {v.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
