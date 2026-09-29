"use client";

import { ScrollText } from "lucide-react";
import { useState } from "react";
import { Coords } from "@/components/game/icons";
import { ResourceValue } from "@/components/game/resource";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable } from "@/components/ui/data-table";
import { SegmentedControl } from "@/components/ui/segmented";
import type { Schemas } from "@/lib/api";
import { num, short } from "@/lib/format";
import type { Resource } from "@/lib/game";
import { cn } from "@/lib/utils";
import { RESULTS, resultOf, type Result } from "./results";

type Report = Schemas["ReportOut"];
type Filter = "all" | Result;

function Dot({ result }: { result: string | null }) {
  const r = resultOf(result);
  const label = r ? RESULTS[r].label : "Sem resultado";
  return <span title={label} className={cn("inline-block size-2.5 shrink-0 rounded-full", r ? RESULTS[r].dot : "border border-border")}><span className="sr-only">{label}</span></span>;
}

function Loot({ report, kind }: { report: Report; kind: Resource }) {
  const value = report[`loot_${kind}`];
  return value ? <ResourceValue kind={kind} value={value} className="text-[13px]" /> : <span className="text-muted-foreground">—</span>;
}

function haul(r: Report) {
  const loot = r.loot_wood + r.loot_clay + r.loot_iron;
  if (!loot) return <span className="text-muted-foreground">—</span>;
  const full = r.haul_total != null && loot >= r.haul_total;
  return (
    <span className="font-mono text-[13px] tabular-nums">
      <span className={full ? "text-gold" : undefined}>{num(loot)}</span>
      {r.haul_total ? <span className="text-muted-foreground">/{num(r.haul_total)}</span> : null}
    </span>
  );
}

export function ReportsTable({ reports }: { reports: Report[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const count = (key: Result) => reports.filter((r) => r.result === key).length;
  const rows = filter === "all" ? reports : reports.filter((r) => r.result === filter);
  const options = [
    { id: "all" as Filter, label: "Todos", hint: String(reports.length) },
    ...(Object.keys(RESULTS) as Result[]).map((key) => ({ id: key as Filter, label: RESULTS[key].short, hint: String(count(key)) })),
  ];

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <SegmentedControl label="Filtrar por resultado" value={filter} options={options} onChange={setFilter} className="min-w-[480px] md:w-[600px]" />
      </div>
      <DataTable
        title="Relatórios de batalha"
        rows={rows}
        rowKey={(r) => r.game_id}
        noun={["relatório", "relatórios"]}
        meta={`${num(reports.filter((r) => r.is_new).length)} novos`}
        empty={{ icon: ScrollText, title: "Nenhum relatório", text: filter === "all" ? "Os relatórios aparecem aqui depois da próxima sincronização." : "Nenhum relatório com esse resultado." }}
        minWidth={960}
        columns={[
          {
            key: "title",
            label: "Assunto",
            width: 32,
            render: (r) => (
              <span className="flex min-w-0 items-center gap-2.5">
                <Dot result={r.result} />
                <Cell className={r.is_new ? "font-semibold" : "text-secondary"} title={r.title}>{r.title}</Cell>
                {r.is_new && <Badge tone="ok" className="shrink-0">novo</Badge>}
              </span>
            ),
          },
          { key: "target", label: "Alvo", width: 9, render: (r) => r.target_coords ? <Coords value={r.target_coords} /> : <Cell muted>—</Cell> },
          { key: "received", label: "Recebido", width: 12, hide: "sm", render: (r) => <Cell mono muted>{short(r.received_at)}</Cell> },
          { key: "wood", label: "Madeira", width: 10, align: "right", hide: "lg", render: (r) => <Loot report={r} kind="wood" /> },
          { key: "clay", label: "Argila", width: 10, align: "right", hide: "lg", render: (r) => <Loot report={r} kind="clay" /> },
          { key: "iron", label: "Ferro", width: 10, align: "right", hide: "lg", render: (r) => <Loot report={r} kind="iron" /> },
          { key: "haul", label: "Saque", width: 17, align: "right", render: haul },
        ]}
      />
    </div>
  );
}
