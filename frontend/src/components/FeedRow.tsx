"use client";

import { useCallback, useRef } from "react";
import type { FeedRow } from "@/lib/api";
import { api } from "@/lib/api";
import { PaperCard } from "./PaperCard";
import Link from "next/link";

interface FeedRowProps {
  row: FeedRow;
  onSave?: (id: number) => void;
}

export function FeedRowSection({ row, onSave }: FeedRowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleClick = (id: number) => {
    api.recordEvent(id, "click").catch(() => {});
  };

  const scrollBy = useCallback((delta: number) => {
    scrollRef.current?.scrollBy({ left: delta, behavior: "smooth" });
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    const el = scrollRef.current;
    if (!el) return;
    if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
    e.preventDefault();
    el.scrollLeft += e.deltaY;
  }, []);

  if (!row.papers?.length) return null;

  return (
    <section className="feed-row">
      <div className="feed-row__header">
        <div>
          <h2>{row.title}</h2>
          <p className="feed-row__hint">Scroll sideways with mouse wheel or arrows</p>
        </div>
        <Link href={`/search?q=${encodeURIComponent(row.title)}`} className="feed-row__more">
          Explore
        </Link>
      </div>
      <div className="row-scroll-wrap">
        <button
          type="button"
          className="row-scroll-btn row-scroll-btn--left"
          onClick={() => scrollBy(-360)}
          aria-label="Scroll left"
        >
          ‹
        </button>
        <div
          className="row-scroll"
          ref={scrollRef}
          onWheel={handleWheel}
        >
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
        <button
          type="button"
          className="row-scroll-btn row-scroll-btn--right"
          onClick={() => scrollBy(360)}
          aria-label="Scroll right"
        >
          ›
        </button>
      </div>
    </section>
  );
}
