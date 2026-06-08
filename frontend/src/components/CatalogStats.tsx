"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

function formatCount(n: number): string {
  return n.toLocaleString();
}

export function CatalogStats() {
  const [total, setTotal] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getStats()
      .then((data) => {
        if (!cancelled) setTotal(data.total_papers);
      })
      .catch(() => {
        if (!cancelled) setTotal(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (total === null) return null;

  return (
    <p className="catalog-stats" title="Total open-access papers in the catalog">
      <span className="catalog-stats__count">{formatCount(total)}</span>
      <span className="catalog-stats__label">papers crawled</span>
    </p>
  );
}
