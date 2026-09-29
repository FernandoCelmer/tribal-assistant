"use client";

import { Flag, Trash2 } from "lucide-react";
import { Coords } from "@/components/game/icons";
import { ActionButton } from "@/components/ui/action-button";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable } from "@/components/ui/data-table";
import type { Schemas } from "@/lib/api";
import { num, relative, short } from "@/lib/format";

type Target = Schemas["FarmTarget"];

export function FarmTable({ targets }: { targets: Target[] }) {
  const active = targets.filter((t) => t.enabled).length;

  return (
    <DataTable
      title="Alvos de farm"
      rows={targets}
      rowKey={(t) => String(t.id)}
      noun={["alvo", "alvos"]}
      meta={`${num(active)} ativos`}
      empty={{ icon: Flag, title: "Nenhum alvo", text: "Adicione acima ou pela página Arredores." }}
      minWidth={760}
      rowClassName={(t) => (t.enabled ? undefined : "opacity-50")}
      columns={[
        { key: "coords", label: "Coords", width: 16, render: (t) => <Coords value={t.coords} className="text-foreground" /> },
        { key: "template", label: "Modelo", width: 10, render: (t) => <Badge className="font-mono">{t.template}</Badge> },
        { key: "wall", label: "Muralha", width: 10, align: "right", render: (t) => <Cell mono className={t.wall_level ? "text-status-warn" : "text-secondary"}>{t.wall_level}</Cell> },
        { key: "enabled", label: "Ativo", width: 12, render: (t) => <Badge tone={t.enabled ? "success" : "neutral"}>{t.enabled ? "sim" : "não"}</Badge> },
        { key: "last", label: "Último ataque", width: 22, render: (t) => <Cell muted title={short(t.last_attack_at)}>{t.last_attack_at ? relative(t.last_attack_at) : "nunca"}</Cell> },
        { key: "loot", label: "Último saque", width: 18, align: "right", render: (t) => <Cell mono className={t.last_loot ? "text-gold" : "text-muted-foreground"}>{num(t.last_loot)}</Cell> },
        {
          key: "remove",
          label: "",
          width: 12,
          align: "right",
          render: (t) => (
            <ActionButton size="icon" variant="ghost" method="DELETE" path={`/api/v1/farm/targets/${t.id}`} confirm={`Remover ${t.coords} do farm?`} done={() => `${t.coords} removida do farm`} aria-label={`Remover ${t.coords}`} title="Remover alvo">
              <Trash2 className="size-4" strokeWidth={1.75} />
            </ActionButton>
          ),
        },
      ]}
    />
  );
}
