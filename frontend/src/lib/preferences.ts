export type ThemeId = "dark" | "light" | "midnight" | "ocean";
export type FeedViewId = "carousel" | "youtube";

const THEME_KEY = "research-feed-theme";
const VIEW_KEY = "research-feed-view";

export const THEMES: { id: ThemeId; label: string }[] = [
  { id: "dark", label: "Dark" },
  { id: "light", label: "Light" },
  { id: "midnight", label: "Midnight" },
  { id: "ocean", label: "Ocean" },
];

export const FEED_VIEWS: { id: FeedViewId; label: string }[] = [
  { id: "carousel", label: "Carousel" },
  { id: "youtube", label: "YouTube" },
];

export function getTheme(): ThemeId {
  if (typeof window === "undefined") return "dark";
  const stored = localStorage.getItem(THEME_KEY) as ThemeId | null;
  return THEMES.some((t) => t.id === stored) ? stored! : "dark";
}

export function setTheme(theme: ThemeId): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(THEME_KEY, theme);
  document.documentElement.setAttribute("data-theme", theme);
}

export function getFeedView(): FeedViewId {
  if (typeof window === "undefined") return "carousel";
  const stored = localStorage.getItem(VIEW_KEY) as FeedViewId | null;
  return FEED_VIEWS.some((v) => v.id === stored) ? stored! : "carousel";
}

export function setFeedView(view: FeedViewId): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(VIEW_KEY, view);
}

export function applyTheme(theme: ThemeId): void {
  document.documentElement.setAttribute("data-theme", theme);
}
