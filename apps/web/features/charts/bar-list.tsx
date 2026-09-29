"use client";

import { useState } from "react";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";
import { NoData } from "./parts";

export type BarRow = { label: string; count: number };

export function BarList({ rows, labelOf = (l) => l, empty, tone = "bg-neutral-300" }: { rows: BarRow[]; labelOf?: (label: string) => string; empty: string; tone?: string }) {
  const [hover, setHover] = useState<string | null>(null);
  const sorted = [...rows].sort((a, b) => b.count - a.count);
  const peak = Math.max(1, ...sorted.map((r) => r.count));
  const total = sorted.reduce((s, r) => s + r.count, 0);

  if (sorted.length === 0) return <NoData text={empty} height={160} />;

  return (
    <ul className="space-y-2.5" onPointerLeave={() => setHover(null)}>
      {sorted.map((r) => (
        <li key={r.label} onPointerEnter={() => setHover(r.label)} className={cn("transition-opacity", hover && hover !== r.label && "opacity-40")}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-[13px]">
            <span className="min-w-0 truncate text-secondary" title={r.label}>{labelOf(r.label)}</span>
            <span className="shrink-0 font-mono text-[12px] tabular-nums">
              {num(r.count)}
              <span className="ml-1.5 text-muted-foreground">{total ? Math.round((r.count / total) * 100) : 0}%</span>
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-hover">
            <div className={cn("h-full rounded-full", tone)} style={{ width: `${(r.count / peak) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
