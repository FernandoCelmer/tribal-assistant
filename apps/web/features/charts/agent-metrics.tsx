"use client";

import { Activity, Ban, ListChecks } from "lucide-react";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Table, Td, Th } from "@/components/ui/table";
import { agentLabel, toolLabel } from "@/features/flow/labels";
import type { Schemas } from "@/lib/api";
import { AGENTS } from "@/lib/game";
import { num, utc } from "@/lib/format";
import { BarList, type BarRow } from "./bar-list";
import { ChartCard, Legend } from "./parts";
import { dayLabel, hourLabel, SHADES, stamp, type Series } from "./scale";
import { StackedBars } from "./stacked-bars";
import { useMounted } from "./use-width";
import { Block } from "@/components/ui/skeleton";

type Stats = Schemas["StatsOut"];

type Bucket = { at: Date; by: Record<string, number> };

function buckets(hourly: Stats["hourly"], daily: boolean): Bucket[] {
  const out = new Map<string, Bucket>();
  for (const h of hourly) {
    const at = utc(h.hour);
    if (daily) at.setHours(0, 0, 0, 0);
    const key = at.toISOString();
    const bucket = out.get(key) ?? { at, by: {} };
    for (const [agent, count] of Object.entries(h.by_agent)) bucket.by[agent] = (bucket.by[agent] ?? 0) + count;
    out.set(key, bucket);
  }
  return [...out.values()].sort((a, b) => a.at.getTime() - b.at.getTime());
}

function agents(list: Bucket[]): string[] {
  const totals = new Map<string, number>();
  for (const b of list) for (const [agent, count] of Object.entries(b.by)) totals.set(agent, (totals.get(agent) ?? 0) + count);
  const order = Object.keys(AGENTS);
  return [...totals.keys()].filter((a) => totals.get(a)).sort((a, b) => (totals.get(b)! - totals.get(a)!) || order.indexOf(a) - order.indexOf(b));
}

function CountTable({ head, rows, labelOf }: { head: string; rows: BarRow[]; labelOf: (l: string) => string }) {
  return (
    <PageScope total={rows.length}>
    <Table>
      <thead><tr><Th>{head}</Th><Th className="text-right">Vezes</Th></tr></thead>
      <tbody>
        {rows.length === 0 && <tr><Td colSpan={2} className="text-secondary">Sem dados.</Td></tr>}
        <PageSlice>{[...rows].sort((a, b) => b.count - a.count).map((r) => (
          <tr key={r.label}><Td>{labelOf(r.label)}</Td><Td className="text-right font-mono tabular-nums">{num(r.count)}</Td></tr>
        ))}</PageSlice>
      </tbody>
    </Table>
    <PageFooter />
    </PageScope>
  );
}

export function AgentMetrics({ stats, hours }: { stats: Stats; hours: number }) {
  const mounted = useMounted();
  if (!mounted) return <div className="space-y-4"><Block className="h-[330px]" /><div className="grid grid-cols-1 gap-4 xl:grid-cols-2"><Block className="h-[260px]" /><Block className="h-[260px]" /></div></div>;

  const daily = hours > 48;
  const list = buckets(stats.hourly, daily);
  const names = agents(list);
  const series: Series[] = names.map((a, i) => ({ key: a, label: agentLabel(a), tone: SHADES[i % SHADES.length], values: list.map((b) => b.by[a] ?? 0) }));
  const labels = list.map((b) => (daily ? dayLabel(b.at) : hourLabel(b.at)));
  const titles = list.map((b) => (daily ? b.at.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit" }) : stamp(b.at)));
  const active = list.filter((b) => Object.values(b.by).some(Boolean));

  return (
    <div className="space-y-4">
      <ChartCard
        title={<><Activity className="size-4 text-secondary" strokeWidth={1.75} />{daily ? "Ações por dia, por agente" : "Ações por hora, por agente"}</>}
        description={`${num(stats.actions_ok + stats.actions_refused + stats.actions_failed)} ações em ${num(stats.runs)} rodadas`}
        legend={<Legend items={series} />}
        chart={<StackedBars labels={labels} titles={titles} series={series} label="Ações por período e agente" />}
        table={
          <PageScope total={active.length}>
          <Table>
            <thead>
              <tr>
                <Th>{daily ? "Dia" : "Hora"}</Th>
                {series.map((s) => <Th key={s.key} className="text-right whitespace-nowrap">{s.label}</Th>)}
                <Th className="text-right">Total</Th>
              </tr>
            </thead>
            <tbody>
              {active.length === 0 && <tr><Td colSpan={series.length + 2} className="text-secondary">Nenhuma ação no período.</Td></tr>}
              <PageSlice>{active.map((b) => (
                <tr key={b.at.toISOString()}>
                  <Td className="whitespace-nowrap font-mono text-[13px]">{daily ? dayLabel(b.at) : stamp(b.at)}</Td>
                  {series.map((s) => <Td key={s.key} className="text-right font-mono tabular-nums">{num(b.by[s.key] ?? 0)}</Td>)}
                  <Td className="text-right font-mono tabular-nums">{num(Object.values(b.by).reduce((x, y) => x + y, 0))}</Td>
                </tr>
              ))}</PageSlice>
            </tbody>
          </Table>
          <PageFooter noun={["período", "períodos"]} />
          </PageScope>
        }
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard
          title={<><Ban className="size-4 text-secondary" strokeWidth={1.75} />Motivos de recusa das travas</>}
          description="Por que a segurança barrou uma ação"
          chart={<BarList rows={stats.refusals} empty="Nenhuma recusa no período." tone="bg-status-warn/70" />}
          table={<CountTable head="Motivo" rows={stats.refusals} labelOf={(l) => l} />}
        />
        <ChartCard
          title={<><ListChecks className="size-4 text-secondary" strokeWidth={1.75} />Ações por tipo</>}
          description="O que os agentes mais fizeram"
          chart={<BarList rows={stats.by_action} labelOf={toolLabel} empty="Nenhuma ação no período." />}
          table={<CountTable head="Ação" rows={stats.by_action} labelOf={toolLabel} />}
        />
      </div>
    </div>
  );
}
