const STORAGE_KEY = "research-feed-seen-ids";
const MAX_SEEN = 2000;

function readIds(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((id) => typeof id === "number" && Number.isFinite(id));
  } catch {
    return [];
  }
}

function writeIds(ids: number[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Ignore quota / private-mode errors
  }
}

/** Paper IDs the browser has already shown in the feed carousel. */
export function getSeenPaperIds(): number[] {
  return readIds();
}

/** Remember papers from the latest feed response so the next load can skip them. */
export function recordShownPaperIds(ids: number[]): void {
  if (!ids.length) return;
  const merged = [...readIds()];
  for (const id of ids) {
    if (!merged.includes(id)) merged.push(id);
  }
  while (merged.length > MAX_SEEN) {
    merged.shift();
  }
  writeIds(merged);
}

export function clearSeenPaperIds(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}
