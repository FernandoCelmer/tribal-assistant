"use client";

import { Hammer } from "lucide-react";
import { Cost } from "@/components/game/resource";
import { BuildingIcon } from "@/components/game/icons";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable, Inline } from "@/components/ui/data-table";
import type { Schemas } from "@/lib/api";
import { duration, num, relative } from "@/lib/format";

type Building = Schemas["BuildingOut"];

function status(b: Building) {
  if (b.next_level == null) return <Badge tone="ok">nível máximo</Badge>;
  if (b.can_build) return <Badge tone="success">pode construir</Badge>;
  if (b.blocker) return <Badge title={b.blocker} className="max-w-full truncate">{b.blocker}</Badge>;
  return <Badge tone="warning">sem recursos</Badge>;
}

export function BuildingsTable({ buildings }: { buildings: Building[] }) {
  const ready = buildings.filter((b) => b.can_build).length;

  return (
    <DataTable
      title="Edifícios"
      rows={buildings}
      rowKey={(b) => b.name}
      noun={["edifício", "edifícios"]}
      meta={`${num(ready)} prontos para subir`}
      empty={{ icon: Hammer, title: "Sem dados de edifícios", text: "Sincronize a aldeia na Visão geral." }}
      minWidth={880}
      rowClassName={(b) => (b.level === 0 && !b.can_build && !b.queued_level ? "opacity-50" : undefined)}
      columns={[
        { key: "building", label: "Edifício", width: 20, render: (b) => <Inline><BuildingIcon name={b.name} level={b.level} className="size-7" /><span className="truncate">{b.label}</span></Inline> },
        { key: "level", label: "Nível", width: 9, align: "right", render: (b) => <span className="tabular-nums"><span className="font-medium">{b.level}</span>{b.max_level ? <span className="text-muted-foreground">/{b.max_level}</span> : null}</span> },
        { key: "queue", label: "Fila", width: 11, render: (b) => b.queued_level ? <Cell className="text-gold" title={b.queued_until ?? undefined}>→ {b.queued_level} <span className="text-muted-foreground">{relative(b.queued_until)}</span></Cell> : <Cell muted>—</Cell> },
        { key: "cost", label: "Próximo nível", width: 30, hide: "lg", render: (b) => b.next_wood == null ? <Cell muted>—</Cell> : <Cost wood={b.next_wood} clay={b.next_clay} iron={b.next_iron} className="flex-nowrap" /> },
        { key: "pop", label: "Pop", width: 6, align: "right", hide: "xl", render: (b) => <Cell mono muted>{num(b.next_pop)}</Cell> },
        { key: "time", label: "Tempo", width: 9, hide: "md", render: (b) => <Cell mono muted>{duration(b.build_time)}</Cell> },
        { key: "status", label: "Status", width: 15, render: status },
      ]}
    />
  );
}
