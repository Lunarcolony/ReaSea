import type { Paper } from "@/lib/api";

export function paperAbstract(paper: Paper): string {
  const snippet = paper.abstract_snippet?.trim();
  const full = paper.full_abstract?.trim();
  const text =
    (snippet && !snippet.startsWith("Abstract not available") ? snippet : null) || full;
  return text || "Abstract not available. Open the paper to read more from the source.";
}

export function formatAuthors(authors?: string, max = 80): string {
  if (!authors) return "Unknown authors";
  return authors.length > max ? authors.slice(0, max) + "..." : authors;
}

export function formatDate(date?: string | null): string {
  if (!date) return "";
  try {
    return new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return date.slice(0, 10);
  }
}

export function formatCitations(count: number): string {
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k citations`;
  return `${count} citation${count === 1 ? "" : "s"}`;
}
