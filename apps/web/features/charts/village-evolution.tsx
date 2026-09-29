"use client";

import { Castle, Coins, Trophy, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { UnitIcon } from "@/components/game/icons";
import { Block } from "@/components/ui/skeleton";
import { Select } from "@/components/ui/select";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Table, Td, Th } from "@/components/ui/table";
import type { Schemas } from "@/lib/api";
import { num, utc } from "@/lib/format";
import { RESOURCES } from "@/lib/game";
import { LineChart } from "./line-chart";
import { ChartCard, Legend } from "./parts";
import { useQueryNav } from "./period-control";
import { RESOURCE_TONES, stamp, type Series } from "./scale";
import { useMounted } from "./use-width";

type Snapshot = Schemas["SnapshotOut"];
type Village = { id: number; name: string; coords: string };

type Figure = { key: string; title: string; icon: LucideIcon | null; series: Series[]; zero?: boolean };

function figures(rows: Snapshot[]): Figure[] {
  const pick = (k: keyof Snapshot) => rows.map((r) => Number(r[k]));
  return [
    { key: "points", title: "Pontos", icon: Trophy, zero: false, series: [{ key: "points", label: "Pontos", tone: "text-neutral-100", values: pick("points") }] },
    {
      key: "resources",
      title: "Recursos em estoque",
      icon: Coins,
      series: [
        { key: "wood", label: RESOURCES.wood.label, tone: RESOURCE_TONES.wood, values: pick("wood") },
        { key: "clay", label: RESOURCES.clay.label, tone: RESOURCE_TONES.clay, values: pick("clay") },
        { key: "iron", label: RESOURCES.iron.label, tone: RESOURCE_TONES.iron, values: pick("iron") },
        { key: "storage", label: "Armazém", tone: "text-neutral-500", values: pick("storage"), dashed: true },
      ],
    },
    {
      key: "population",
      title: "População",
      icon: Users,
      series: [
        { key: "pop_current", label: "Em uso", tone: "text-neutral-100", values: pick("pop_current") },
        { key: "pop_max", label: "Limite da fazenda", tone: "text-neutral-500", values: pick("pop_max"), dashed: true },
      ],
    },
    {
      key: "troops",
      title: "Tropas",
      icon: null,
      series: [
        { key: "troops_total", label: "Total", tone: "text-neutral-100", values: pick("troops_total") },
        { key: "troops_home", label: "Em casa", tone: "text-neutral-500", values: pick("troops_home") },
      ],
    },
  ];
}

function SnapshotTable({ times, series }: { times: number[]; series: Series[] }) {
  const order = times.map((_, i) => i).reverse();
  return (
    <PageScope total={order.length}>
    <Table>
      <thead>
        <tr>
          <Th>Sincronização</Th>
          {series.map((s) => <Th key={s.key} className="text-right whitespace-nowrap">{s.label}</Th>)}
        </tr>
      </thead>
      <tbody>
        {order.length === 0 && <tr><Td colSpan={series.length + 1} className="text-secondary">Sem sincronizações no período.</Td></tr>}
        <PageSlice>{order.map((i) => (
          <tr key={times[i]}>
            <Td className="whitespace-nowrap font-mono text-[13px]">{stamp(new Date(times[i]))}</Td>
            {series.map((s) => <Td key={s.key} className="text-right font-mono tabular-nums">{num(s.values[i])}</Td>)}
          </tr>
        ))}</PageSlice>
      </tbody>
    </Table>
    <PageFooter noun={["sincronização", "sincronizações"]} />
    </PageScope>
  );
}

export function VillageEvolution({ rows, villages, village }: { rows: Snapshot[]; villages: Village[]; village: number | null }) {
  const mounted = useMounted();
  const { set, pending } = useQueryNav();
  const sorted = [...rows].sort((a, b) => utc(a.taken_at).getTime() - utc(b.taken_at).getTime());
  const times = sorted.map((r) => utc(r.taken_at).getTime());

  return (
    <section className="space-y-4" aria-labelledby="evolution-title">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="evolution-title" className="flex items-center gap-2 text-base font-semibold"><Castle className="size-4 text-secondary" strokeWidth={1.75} />Evolução da aldeia</h2>
          <p className="mt-0.5 text-[13px] text-secondary">Um ponto por sincronização · {num(sorted.length)} no período</p>
        </div>
        {villages.length > 1 && (
          <Select
            aria-label="Aldeia"
            value={String(village ?? "")}
            onChange={(v) => set({ village: v })}
            options={villages.map((v) => ({ value: String(v.id), label: v.name, hint: v.coords }))}
            className={pending ? "opacity-60 sm:w-64" : "sm:w-64"}
          />
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {figures(sorted).map((f) => {
          const Icon = f.icon;
          return mounted ? (
            <ChartCard
              key={f.key}
              title={<>{Icon ? <Icon className="size-4 text-secondary" strokeWidth={1.75} /> : <UnitIcon name="axe" className="size-4" />}{f.title}</>}
              legend={<Legend items={f.series} />}
              chart={<LineChart times={times} series={f.series} label={f.title} zero={f.zero ?? true} />}
              table={<SnapshotTable times={times} series={f.series} />}
            />
          ) : <Block key={f.key} className="h-[290px]" />;
        })}
      </div>
    </section>
  );
}
