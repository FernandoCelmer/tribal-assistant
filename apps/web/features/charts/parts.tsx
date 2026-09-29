"use client";

import { ChartColumn, Table2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { cn } from "@/lib/utils";

export type TipRow = { label: string; value: string; tone?: string };

export function Tooltip({ x, y, width, title, rows }: { x: number; y: number; width: number; title: string; rows: TipRow[] }) {
  const box = 200;
  const left = x + 14 + box > width ? Math.max(0, x - box - 14) : x + 14;
  return (
    <div role="status" className="pointer-events-none absolute z-10 w-[200px] rounded-md border border-border bg-background/95 px-3 py-2 text-[12px] backdrop-blur-sm" style={{ left, top: Math.max(0, y) }}>
      <div className="mb-1 font-medium text-foreground">{title}</div>
      <ul className="space-y-0.5">
        {rows.map((r) => (
          <li key={r.label} className="flex items-center gap-2 text-secondary">
            {r.tone && <i aria-hidden className={cn("size-2 shrink-0 rounded-[2px] bg-current", r.tone)} />}
            <span className="min-w-0 flex-1 truncate">{r.label}</span>
            <b className="font-mono font-medium tabular-nums text-foreground">{r.value}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Legend({ items }: { items: { key: string; label: string; tone: string; dashed?: boolean }[] }) {
  if (items.length < 2) return null;
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] text-secondary">
      {items.map((i) => (
        <li key={i.key} className="inline-flex items-center gap-1.5">
          <i aria-hidden className={cn("h-0.5 w-3 shrink-0 rounded-full bg-current", i.tone, i.dashed && "opacity-60")} />
          {i.label}
        </li>
      ))}
    </ul>
  );
}

export function ChartCard({ title, description, aside, legend, chart, table, className }: { title: ReactNode; description?: ReactNode; aside?: ReactNode; legend?: ReactNode; chart: ReactNode; table?: ReactNode; className?: string }) {
  const [tabular, setTabular] = useState(false);
  return (
    <Panel className={className}>
      <PanelHeader
        title={title}
        description={description}
        aside={
          <div className="flex items-center gap-2">
            {aside}
            {table && (
              <Button size="sm" variant="ghost" aria-pressed={tabular} onClick={() => setTabular((v) => !v)}>
                {tabular ? <ChartColumn className="size-3.5" strokeWidth={1.75} /> : <Table2 className="size-3.5" strokeWidth={1.75} />}
                {tabular ? "Gráfico" : "Tabela"}
              </Button>
            )}
          </div>
        }
      />
      {tabular && table ? (
        <div className="max-h-[360px] overflow-y-auto">{table}</div>
      ) : (
        <div className="space-y-3 p-4">
          {legend}
          {chart}
        </div>
      )}
    </Panel>
  );
}

export function NoData({ text, height = 200 }: { text: string; height?: number }) {
  return (
    <div className="flex items-center justify-center rounded-md border border-dashed border-border-subtle px-4 text-center text-[13px] text-muted-foreground" style={{ height }}>
      {text}
    </div>
  );
}
