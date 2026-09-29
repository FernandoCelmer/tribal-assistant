"use client";

import { useState } from "react";
import { num } from "@/lib/format";
import { NoData, Tooltip } from "./parts";
import { compact, ticks, type Series } from "./scale";
import { useWidth } from "./use-width";

const PAD = { top: 10, right: 8, bottom: 24, left: 36 };

export function StackedBars({ labels, titles, series, height = 220, label, empty = "Nenhuma ação no período." }: { labels: string[]; titles: string[]; series: Series[]; height?: number; label: string; empty?: string }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const totals = labels.map((_, i) => series.reduce((sum, s) => sum + (s.values[i] ?? 0), 0));
  const peak = Math.max(0, ...totals);

  if (labels.length === 0 || peak === 0) return <div ref={ref}><NoData text={empty} height={height} /></div>;

  const scale = ticks(peak);
  const top = scale[scale.length - 1];
  const inner = { w: width - PAD.left - PAD.right, h: height - PAD.top - PAD.bottom };
  const step = inner.w / labels.length;
  const bar = Math.max(1, Math.min(16, step * 0.62));
  const y = (v: number) => PAD.top + inner.h - (v / top) * inner.h;
  const every = Math.max(1, Math.ceil(labels.length / Math.max(2, Math.floor(inner.w / 48))));

  return (
    <div ref={ref} className="relative w-full select-none" onPointerLeave={() => setHover(null)}>
      <svg
        role="img"
        aria-label={label}
        width={width}
        height={height}
        className="block touch-none"
        onPointerMove={(e) => {
          const px = e.clientX - e.currentTarget.getBoundingClientRect().left - PAD.left;
          const i = Math.floor(px / step);
          setHover(i >= 0 && i < labels.length ? i : null);
        }}
      >
        {scale.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} className="stroke-border-subtle" strokeWidth={1} />
            <text x={PAD.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="fill-muted-foreground font-mono text-[10px]">{compact(t)}</text>
          </g>
        ))}
        {hover !== null && <rect x={PAD.left + hover * step} y={PAD.top} width={step} height={inner.h} className="fill-surface-hover" />}
        {labels.map((l, i) => {
          const cx = PAD.left + i * step + step / 2;
          let base = 0;
          return (
            <g key={i} opacity={hover === null || hover === i ? 1 : 0.4}>
              {series.map((s) => {
                const v = s.values[i] ?? 0;
                if (!v) return null;
                const y0 = y(base);
                base += v;
                const y1 = y(base);
                return <rect key={s.key} x={cx - bar / 2} y={y1} width={bar} height={Math.max(1, y0 - y1 - 1)} fill="currentColor" className={s.tone} rx={1} />;
              })}
              {i % every === 0 && <text x={cx} y={height - 6} textAnchor="middle" className="fill-muted-foreground font-mono text-[10px]">{l}</text>}
            </g>
          );
        })}
      </svg>
      {hover !== null && (
        <Tooltip
          x={PAD.left + hover * step + step / 2}
          y={PAD.top}
          width={width}
          title={`${titles[hover]} · ${num(totals[hover])}`}
          rows={series.filter((s) => s.values[hover]).map((s) => ({ label: s.label, value: num(s.values[hover]), tone: s.tone }))}
        />
      )}
    </div>
  );
}
