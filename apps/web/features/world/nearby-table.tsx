"use client";

import { Flag, Map as MapIcon, Plus } from "lucide-react";
import { Coords, UnitIcon } from "@/components/game/icons";
import { ActionButton } from "@/components/ui/action-button";
import { Badge } from "@/components/ui/badge";
import { Cell, DataTable, Inline, type Column } from "@/components/ui/data-table";
import type { Schemas } from "@/lib/api";
import { duration, num } from "@/lib/format";
import { UNITS } from "@/lib/game";

type Nearby = Schemas["NearbyVillage"];

const TRAVEL = ["spear", "light", "ram"] as const;

function travel(n: Nearby, unit: string) {
  const minutes = n.travel_minutes[unit];
  return minutes == null ? "—" : duration(minutes * 60);
}

function owner(n: Nearby) {
  if (n.is_barbarian) return <Cell muted>bárbara</Cell>;
  return <Cell title={n.player_name ?? undefined}>{n.player_name ?? "?"}{n.ally_tag && <span className="ml-1 text-muted-foreground">[{n.ally_tag}]</span>}</Cell>;
}

function action(n: Nearby) {
  if (!n.is_barbarian) return null;
  if (n.is_farm_target) return <Badge tone="success"><Flag className="mr-1 size-3" />no farm</Badge>;
  return (
    <ActionButton
      size="sm"
      variant="outline"
      path="/api/v1/farm/targets"
      body={{ coords: n.coords, template: "A", wall_level: 0 }}
      done={() => `${n.coords} adicionada ao farm`}
      aria-label={`Adicionar ${n.coords} ao farm`}
    >
      <Plus className="size-3.5" strokeWidth={2} />farm
    </ActionButton>
  );
}

export function NearbyTable({ rows, radius, description }: { rows: Nearby[]; radius: number; description?: string }) {
  const barbarians = rows.filter((n) => n.is_barbarian).length;
  const columns: Column<Nearby>[] = [
    { key: "village", label: "Aldeia", width: 22, render: (n) => <span className="block min-w-0"><Cell className="font-medium" title={n.name}>{n.name}</Cell><Coords value={n.coords} className="md:hidden" /></span> },
    { key: "coords", label: "Coords", width: 9, hide: "md", render: (n) => <Coords value={n.coords} /> },
    { key: "points", label: "Pontos", width: 9, align: "right", render: (n) => <Cell className="tabular-nums">{num(n.points)}</Cell> },
    { key: "distance", label: "Distância", width: 9, align: "right", render: (n) => <Cell mono>{n.distance.toFixed(1)}</Cell> },
    { key: "owner", label: "Dono", width: 16, hide: "lg", render: owner },
    ...TRAVEL.map((unit): Column<Nearby> => ({
      key: unit,
      label: UNITS[unit] ?? unit,
      width: 9,
      align: "right",
      hide: unit === "ram" ? "xl" : undefined,
      render: (n) => <Inline className="justify-end"><UnitIcon name={unit} className="size-4" /><span className="font-mono text-[13px] text-secondary">{travel(n, unit)}</span></Inline>,
    })),
    { key: "action", label: "", width: 9, align: "right", render: action },
  ];

  return (
    <DataTable
      title="Aldeias próximas"
      rows={rows}
      rowKey={(n) => String(n.id)}
      noun={["aldeia", "aldeias"]}
      meta={`raio ${radius} · ${num(barbarians)} bárbaras`}
      description={description}
      empty={{ icon: MapIcon, title: "Nada neste raio", text: "Aumente o raio ou troque o tipo de aldeia." }}
      minWidth={960}
      columns={columns}
    />
  );
}
