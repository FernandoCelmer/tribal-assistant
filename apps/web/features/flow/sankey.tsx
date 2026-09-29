"use client";

import { useState } from "react";
import { NoData, Tooltip, type TipRow } from "@/features/charts/parts";
import { SHADES } from "@/features/charts/scale";
import { useWidth } from "@/features/charts/use-width";
import type { Schemas } from "@/lib/api";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";
import { agentLabel, OUTCOMES, outcomeLabel, toolLabel } from "./labels";

type Flow = Schemas["FlowOut"];
type Node = Schemas["FlowNode"];
type Placed = Node & { x: number; y: number; h: number; out: number; in: number };
type Band = { id: string; d: string; tone: string; agent: string | null; tool: string; title: string; count: number; unit: string };

const NODE = 10;
const GAP = 14;
const TOP = 12;

function place(nodes: Node[], x: number, scale: number): Record<string, Placed> {
  let y = TOP;
  const out: Record<string, Placed> = {};
  for (const n of nodes) {
    const h = Math.max(3, n.count * scale);
    out[n.id] = { ...n, x, y, h, out: y, in: y };
    y += h + GAP;
  }
  return out;
}

function band(x0: number, y0: number, x1: number, y1: number, h: number): string {
  const m = (x0 + x1) / 2;
  return `M${x0},${y0}C${m},${y0} ${m},${y1} ${x1},${y1}L${x1},${y1 + h}C${m},${y1 + h} ${m},${y0 + h} ${x0},${y0 + h}Z`;
}

export function Sankey({ data }: { data: Flow }) {
  const [ref, width] = useWidth<HTMLDivElement>(900);
  const [focus, setFocus] = useState<{ band: Band; x: number; y: number } | null>(null);

  if (!data.calls) return <div ref={ref}><NoData text="Nenhuma ferramenta usada no período. Rode uma rodada de agentes." height={200} /></div>;

  const narrow = width < 640;
  const label = narrow ? 92 : 168;
  const rows = Math.max(data.agents.length, data.tools.length, data.outcomes.length);
  const height = Math.max(300, rows * 40 + TOP * 2);
  const usable = height - TOP * 2;
  const columns = [data.agents, data.tools, data.outcomes];
  const scale = Math.min(...columns.map((col) => (usable - GAP * Math.max(0, col.length - 1)) / Math.max(1, col.reduce((s, n) => s + n.count, 0))));
  const xTools = Math.round((width - NODE) * (narrow ? 0.4 : 0.44));
  const xOutcomes = width - NODE - label;

  const shade = Object.fromEntries(data.agents.map((a, i) => [a.id, SHADES[i % SHADES.length]]));
  const agents = place(data.agents, 0, scale);
  const tools = place(data.tools, xTools, scale);
  const outcomes = place(data.outcomes, xOutcomes, scale);
  const bands: Band[] = [];

  for (const l of data.agent_tool) {
    const a = agents[l.source];
    const t = tools[l.target];
    if (!a || !t) continue;
    const h = l.count * scale;
    bands.push({ id: `a:${l.source}:${l.target}`, d: band(a.x + NODE, a.out, t.x, t.in, h), tone: shade[l.source] ?? "text-neutral-400", agent: l.source, tool: l.target, title: `${agentLabel(l.source)} → ${toolLabel(l.target)}`, count: l.count, unit: "chamadas" });
    a.out += h;
    t.in += h;
  }

  for (const l of data.tool_outcome) {
    const t = tools[l.source];
    const o = outcomes[l.target];
    if (!t || !o) continue;
    const h = l.count * scale;
    bands.push({ id: `t:${l.source}:${l.target}`, d: band(t.x + NODE, t.out, o.x, o.in, h), tone: OUTCOMES[l.target]?.tone ?? "text-neutral-500", agent: null, tool: l.source, title: `${toolLabel(l.source)} → ${outcomeLabel(l.target)}`, count: l.count, unit: "vezes" });
    t.out += h;
    o.in += h;
  }

  const related = (b: Band) => {
    if (!focus) return true;
    const f = focus.band;
    if (f.agent) return b.agent === f.agent || (b.agent === null && b.tool === f.tool);
    return b.tool === f.tool;
  };

  const nodeLabel = (n: Placed, text: string, anchor: "start" | "end" = "start") => (
    <text x={anchor === "start" ? n.x + NODE + 6 : n.x - 6} y={n.y + Math.min(n.h / 2, 10)} dy="0.32em" textAnchor={anchor} className="pointer-events-none fill-foreground text-[11px] [paint-order:stroke] [stroke-linejoin:round] stroke-background [stroke-width:3px]">
      {narrow && text.length > 14 ? `${text.slice(0, 13)}…` : text}
      <tspan dx={5} className="fill-muted-foreground font-mono text-[10px]">{num(n.count)}</tspan>
    </text>
  );

  const tip: TipRow[] = focus ? [{ label: focus.band.unit, value: num(focus.band.count) }] : [];

  return (
    <div ref={ref} className="relative w-full select-none" onPointerLeave={() => setFocus(null)}>
      <svg role="img" aria-label="Fluxo de agentes para ferramentas e resultados" width={width} height={height} className="block">
        <g>
          {bands.map((b) => (
            <path
              key={b.id}
              d={b.d}
              fill="currentColor"
              className={cn(b.tone, "transition-opacity duration-150")}
              opacity={focus ? (related(b) ? 0.55 : 0.06) : 0.28}
              onPointerMove={(e) => {
                const box = e.currentTarget.ownerSVGElement!.getBoundingClientRect();
                setFocus({ band: b, x: e.clientX - box.left, y: e.clientY - box.top - 20 });
              }}
            />
          ))}
        </g>
        <g>
          {Object.values(agents).map((n) => (
            <g key={n.id}>
              <rect x={n.x} y={n.y} width={NODE} height={n.h} rx={2} fill="currentColor" className={shade[n.id]} />
              {nodeLabel(n, agentLabel(n.id))}
            </g>
          ))}
          {Object.values(tools).map((n) => (
            <g key={n.id}>
              <rect x={n.x} y={n.y} width={NODE} height={n.h} rx={2} className="fill-neutral-600" />
              {nodeLabel(n, toolLabel(n.id))}
            </g>
          ))}
          {Object.values(outcomes).map((n) => (
            <g key={n.id}>
              <rect x={n.x} y={n.y} width={NODE} height={n.h} rx={2} fill="currentColor" className={OUTCOMES[n.id]?.tone ?? "text-neutral-500"} />
              {nodeLabel(n, outcomeLabel(n.id))}
            </g>
          ))}
        </g>
      </svg>
      {focus && <Tooltip x={focus.x} y={focus.y} width={width} title={focus.band.title} rows={tip} />}
    </div>
  );
}
