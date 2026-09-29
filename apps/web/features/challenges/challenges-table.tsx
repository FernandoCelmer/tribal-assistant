"use client";

import { Trophy } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable } from "@/components/ui/data-table";
import { SegmentedControl } from "@/components/ui/segmented";
import { agentLabel } from "@/features/agents/labels";
import type { Schemas } from "@/lib/api";
import { num, percent } from "@/lib/format";
import { cn } from "@/lib/utils";

type Challenge = Schemas["ChallengeOut"];
type Filter = "all" | "auto" | "passive" | "blocked" | "social" | "done";

export const STATUS: Record<Exclude<Filter, "all">, { label: string; tone: "success" | "neutral" | "danger" | "warning" | "ok" }> = {
  auto: { label: "automático", tone: "success" },
  passive: { label: "passivo", tone: "neutral" },
  social: { label: "você decide", tone: "warning" },
  blocked: { label: "fora", tone: "danger" },
  done: { label: "concluído", tone: "ok" },
};

function stateOf(c: Challenge): Exclude<Filter, "all"> {
  return c.done ? "done" : (c.status as Exclude<Filter, "all">);
}

function Progress({ c }: { c: Challenge }) {
  if (c.target == null) return <Cell muted>—</Cell>;
  const ratio = Math.min(1, c.ratio ?? 0);
  return (
    <span className="flex min-w-0 items-center gap-2.5">
      <span className="h-1.5 w-full min-w-10 overflow-hidden rounded-full bg-surface-hover"><span className={cn("block h-full rounded-full", ratio >= 0.9 ? "bg-gold" : "bg-foreground")} style={{ width: percent(ratio) }} /></span>
      <span className="shrink-0 font-mono text-[12px] tabular-nums text-secondary">{num(c.current ?? 0)}/{num(c.target)}</span>
    </span>
  );
}

export function ChallengesTable({ items }: { items: Challenge[] }) {
  const [filter, setFilter] = useState<Filter>("auto");
  const count = (key: Filter) => (key === "all" ? items.length : items.filter((c) => stateOf(c) === key).length);
  const rows = (filter === "all" ? items : items.filter((c) => stateOf(c) === filter)).toSorted((a, b) => (b.ratio ?? 0) - (a.ratio ?? 0));
  const options = (["all", "auto", "passive", "social", "blocked", "done"] as Filter[]).map((id) => ({ id, label: id === "all" ? "Todos" : STATUS[id].label, hint: String(count(id)) }));

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <SegmentedControl label="Filtrar desafios" value={filter} options={options} onChange={setFilter} className="min-w-[560px] md:w-[720px]" />
      </div>
      <DataTable
        title="Desafios"
        rows={rows}
        rowKey={(c) => `${c.group}:${c.name}`}
        noun={["desafio", "desafios"]}
        empty={{ icon: Trophy, title: "Nenhum desafio aqui", text: items.length ? "Nenhum desafio com esse filtro." : "Os desafios aparecem depois que a tela de conquistas for lida numa sincronização." }}
        minWidth={980}
        columns={[
          {
            key: "name",
            label: "Desafio",
            width: 30,
            render: (c) => (
              <span className="block min-w-0">
                <Cell className="font-medium" title={c.name}>{c.name}{c.level > 0 && <span className="ml-1.5 text-[12px] font-normal text-muted-foreground">nível {c.level}</span>}</Cell>
                <Cell muted className="text-[12px]" title={c.description}>{c.description}</Cell>
              </span>
            ),
          },
          { key: "progress", label: "Progresso", width: 18, render: (c) => <Progress c={c} /> },
          { key: "status", label: "Situação", width: 12, render: (c) => <Badge tone={STATUS[stateOf(c)].tone}>{STATUS[stateOf(c)].label}</Badge> },
          { key: "agent", label: "Quem persegue", width: 13, hide: "lg", render: (c) => <Cell muted>{c.agent ? agentLabel(c.agent) : "—"}</Cell> },
          { key: "how", label: "Como", width: 27, hide: "md", render: (c) => <Cell muted className="text-[13px]" title={c.how}>{c.how}</Cell> },
        ]}
      />
    </div>
  );
}
