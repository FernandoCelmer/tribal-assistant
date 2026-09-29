"use client";

import { Swords } from "lucide-react";
import { Cost } from "@/components/game/resource";
import { UnitIcon } from "@/components/game/icons";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable, Inline } from "@/components/ui/data-table";
import type { Schemas } from "@/lib/api";
import { duration, num } from "@/lib/format";
import { UNITS } from "@/lib/game";

type Unit = Schemas["UnitOut"];

export function TroopsTable({ units }: { units: Unit[] }) {
  const home = units.reduce((sum, u) => sum + u.home, 0);

  return (
    <DataTable
      title="Tropas"
      rows={units}
      rowKey={(u) => u.name}
      noun={["unidade", "unidades"]}
      meta={`${num(home)} em casa`}
      empty={{ icon: Swords, title: "Sem dados de tropas", text: "Sincronize a aldeia na Visão geral." }}
      minWidth={880}
      rowClassName={(u) => (u.total || u.available ? undefined : "opacity-50")}
      columns={[
        { key: "unit", label: "Unidade", width: 20, render: (u) => <Inline><UnitIcon name={u.name} /><span className="truncate">{UNITS[u.name] ?? u.name}</span></Inline> },
        { key: "home", label: "Na aldeia", width: 9, align: "right", render: (u) => <span className="font-medium tabular-nums">{num(u.home)}</span> },
        { key: "away", label: "Fora", width: 8, align: "right", render: (u) => <Cell muted className="tabular-nums">{num(u.away)}</Cell> },
        { key: "total", label: "Total", width: 8, align: "right", render: (u) => <Cell className="tabular-nums">{num(u.total)}</Cell> },
        { key: "recruit", label: "Recrutável", width: 10, align: "right", render: (u) => <Cell mono className={u.available && u.max_recruit ? "text-status-ok" : "text-muted-foreground"}>{u.available ? num(u.max_recruit) : "—"}</Cell> },
        { key: "cost", label: "Custo", width: 22, hide: "lg", render: (u) => u.cost_wood == null ? <Cell muted>—</Cell> : <Cost wood={u.cost_wood} clay={u.cost_clay} iron={u.cost_iron} className="flex-nowrap" /> },
        { key: "time", label: "Tempo", width: 9, hide: "md", render: (u) => <Cell mono muted>{duration(u.build_time)}</Cell> },
        { key: "status", label: "Status", width: 14, render: (u) => u.available ? <Badge tone="success">recrutável</Badge> : <Badge title={u.blocker ?? undefined} className="max-w-full truncate">{u.blocker ?? "indisponível"}</Badge> },
      ]}
    />
  );
}
