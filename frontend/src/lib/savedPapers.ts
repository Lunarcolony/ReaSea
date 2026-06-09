import type { Paper } from "@/lib/api";

const STORAGE_KEY = "research-feed-saved-papers";
const MAX_SAVED = 1000;

function readSaved(): Paper[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((p) => p && typeof p.id === "number");
  } catch {
    return [];
  }
}

function writeSaved(papers: Paper[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(papers));
  } catch {
    // Ignore storage errors (quota/private mode)
  }
}

export function getSavedPapers(): Paper[] {
  return readSaved();
}

export function getSavedPaperIds(): number[] {
  return readSaved().map((p) => p.id);
}

export function isPaperSaved(id: number): boolean {
  return readSaved().some((p) => p.id === id);
}

export function savePaperLocal(paper: Paper): void {
  const existing = readSaved();
  const filtered = existing.filter((p) => p.id !== paper.id);
  const next = [{ ...paper, saved: true }, ...filtered].slice(0, MAX_SAVED);
  writeSaved(next);
}

export function removeSavedPaper(id: number): void {
  const next = readSaved().filter((p) => p.id !== id);
  writeSaved(next);
}

export function toggleSavedPaper(paper: Paper): boolean {
  const alreadySaved = isPaperSaved(paper.id);
  if (alreadySaved) {
    removeSavedPaper(paper.id);
    return false;
  }
  savePaperLocal(paper);
  return true;
}

/** Overlay per-browser saved state onto API paper objects. */
export function applySavedState<T extends Paper>(papers: T[]): T[] {
  const savedIds = new Set(getSavedPaperIds());
  return papers.map((p) => ({ ...p, saved: savedIds.has(p.id) }));
}
