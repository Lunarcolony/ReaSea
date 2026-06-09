const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? "/api" : "http://localhost:8000");

export interface Paper {
  id: number;
  title: string;
  authors: string;
  abstract_snippet: string;
  full_abstract?: string;
  published_date: string | null;
  source_api: string;
  source_url: string;
  pdf_url?: string;
  citation_count: number;
  primary_topic?: string;
  venue?: string;
  trending_score?: number;
  hybrid_impact?: number;
  saved?: boolean;
  similar?: Paper[];
  is_open_access?: boolean;
}

export interface FeedRow {
  id: string;
  title: string;
  papers: Paper[];
}

export interface FeedResponse {
  rows: FeedRow[];
  seed?: number;
  personalized?: boolean;
  refreshed?: boolean;
  shown_ids?: number[];
}

export interface StatsResponse {
  total_papers: number;
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  getStats: (): Promise<StatsResponse> => apiFetch("/stats"),
  getFeed: (refresh = false, excludeIds: number[] = []) => {
    const params = new URLSearchParams();
    if (refresh) params.set("refresh", "true");
    if (excludeIds.length) params.set("exclude", excludeIds.join(","));
    const query = params.toString();
    return apiFetch(`/feed${query ? `?${query}` : ""}`);
  },
  getPaper: (id: number) => apiFetch(`/papers/${id}`),
  search: (q: string, page = 1) => apiFetch(`/search?q=${encodeURIComponent(q)}&page=${page}`),
  getPreferences: () => apiFetch("/users/me/preferences"),
  updatePreferences: (topic_slugs: string[], research_role?: string) =>
    apiFetch("/users/me/preferences", {
      method: "PATCH",
      body: JSON.stringify({ topic_slugs, research_role }),
    }),
  savePaper: (paperId: number) =>
    apiFetch(`/users/me/reading-list/${paperId}`, { method: "POST" }),
  unsavePaper: (paperId: number) =>
    apiFetch(`/users/me/reading-list/${paperId}`, { method: "DELETE" }),
  readingList: () => apiFetch("/users/me/reading-list"),
  recordEvent: (paper_id: number, event_type: string) =>
    apiFetch("/users/me/events", {
      method: "POST",
      body: JSON.stringify({ events: [{ paper_id, event_type }] }),
    }),
};

export const TOPICS = [
  { slug: "artificial-intelligence", label: "Artificial Intelligence" },
  { slug: "machine-learning", label: "Machine Learning" },
  { slug: "deep-learning", label: "Deep Learning" },
  { slug: "computer-vision", label: "Computer Vision" },
  { slug: "bioinformatics", label: "Bioinformatics" },
  { slug: "natural-language-processing", label: "NLP" },
];
