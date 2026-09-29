"use client";

import { useState } from "react";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";
import { NoData, Tooltip } from "./parts";
import { compact, dayLabel, hourLabel, stamp, ticks, type Series } from "./scale";
import { useWidth } from "./use-width";

const PAD = { top: 10, right: 12, bottom: 24, left: 44 };

export function LineChart({ times, series, height = 200, label, format = num, zero = true }: { times: number[]; series: Series[]; height?: number; label: string; format?: (v: number) => string; zero?: boolean }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  if (times.length === 0) return <div ref={ref}><NoData text="Sem sincronizações no período." height={height} /></div>;

  const all = series.flatMap((s) => s.values);
  const high = Math.max(1, ...all);
  const low = zero ? 0 : Math.min(...all);
  const scale = ticks(high - low).map((t) => t + (zero ? 0 : Math.floor(low)));
  const top = scale[scale.length - 1];
  const bottom = scale[0];
  const t0 = times[0];
  const t1 = times[times.length - 1];
  const span = Math.max(1, t1 - t0);
  const inner = { w: width - PAD.left - PAD.right, h: height - PAD.top - PAD.bottom };
  const x = (t: number) => PAD.left + (times.length === 1 ? inner.w / 2 : ((t - t0) / span) * inner.w);
  const y = (v: number) => PAD.top + inner.h - ((v - bottom) / Math.max(1, top - bottom)) * inner.h;
  const daily = span > 2 * 86_400_000;
  const marks = Math.max(2, Math.min(6, Math.floor(inner.w / 90)));
  const xticks = Array.from({ length: marks }, (_, i) => t0 + (span * i) / (marks - 1));

  const nearest = (px: number) => {
    let best = 0;
    for (let i = 1; i < times.length; i++) if (Math.abs(x(times[i]) - px) < Math.abs(x(times[best]) - px)) best = i;
    return best;
  };

  return (
    <div ref={ref} className="relative w-full select-none" onPointerLeave={() => setHover(null)}>
      <svg
        role="img"
        aria-label={label}
        width={width}
        height={height}
        className="block touch-none"
        onPointerMove={(e) => setHover(nearest(e.clientX - e.currentTarget.getBoundingClientRect().left))}
      >
        {scale.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} className="stroke-border-subtle" strokeWidth={1} />
            <text x={PAD.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="fill-muted-foreground font-mono text-[10px]">{compact(t)}</text>
          </g>
        ))}
        {xticks.map((t, i) => (
          <text key={i} x={x(t)} y={height - 6} textAnchor={i === 0 ? "start" : i === marks - 1 ? "end" : "middle"} className="fill-muted-foreground font-mono text-[10px]">
            {daily ? dayLabel(new Date(t)) : hourLabel(new Date(t))}
          </text>
        ))}
        {hover !== null && <line x1={x(times[hover])} x2={x(times[hover])} y1={PAD.top} y2={PAD.top + inner.h} className="stroke-border-hover" strokeWidth={1} />}
        {series.map((s) => (
          <g key={s.key} className={s.tone}>
            <path
              d={s.values.map((v, i) => `${i ? "L" : "M"}${x(times[i]).toFixed(1)},${y(v).toFixed(1)}`).join("")}
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              strokeLinejoin="round"
              strokeLinecap="round"
              strokeDasharray={s.dashed ? "3 3" : undefined}
              opacity={s.dashed ? 0.6 : 1}
            />
            {(times.length === 1 || hover !== null) && (
              <circle cx={x(times[hover ?? 0])} cy={y(s.values[hover ?? 0])} r={3} className="stroke-background" fill="currentColor" strokeWidth={1.5} />
            )}
          </g>
        ))}
      </svg>
      {hover !== null && (
        <Tooltip
          x={x(times[hover])}
          y={PAD.top}
          width={width}
          title={stamp(new Date(times[hover]))}
          rows={series.map((s) => ({ label: s.label, value: format(s.values[hover]), tone: cn(s.tone) }))}
        />
      )}
    </div>
  );
}
