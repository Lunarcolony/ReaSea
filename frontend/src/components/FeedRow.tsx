import type { FeedRow } from "@/lib/api";
import { api } from "@/lib/api";
import { PaperCard } from "./PaperCard";
import Link from "next/link";

interface FeedRowProps {
  row: FeedRow;
  onSave?: (id: number) => void;
}

export function FeedRowSection({ row, onSave }: FeedRowProps) {
  const handleClick = (id: number) => {
    api.recordEvent(id, "click").catch(() => {});
  };

  if (!row.papers?.length) return null;
  return (
    <section className="feed-row">
      <div className="feed-row__header">
        <h2>{row.title}</h2>
        <Link href={`/search?q=${encodeURIComponent(row.title)}`} className="feed-row__more">
          Explore
        </Link>
      </div>
      <div className="row-scroll">
        {row.papers.map((paper) => (
          <PaperCard
            key={paper.id}
            paper={paper}
            onSave={onSave}
            onClick={handleClick}
            variant="feed"
          />
        ))}
      </div>
    </section>
  );
}
