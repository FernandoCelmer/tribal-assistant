"use client";

import { CircleHelp, GitFork, Wallet } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { Table, Td, Th } from "@/components/ui/table";
import { ChartCard } from "@/features/charts/parts";
import { SHADES } from "@/features/charts/scale";
import { readable } from "@/features/flow/labels";
import { Sankey } from "@/features/flow/sankey";
import type { Budget, Cost } from "@/features/strategy/types";
import type { Schemas } from "@/lib/api";
import { duration, num } from "@/lib/format";
import { RESOURCES, type Resource } from "@/lib/game";
import { cn } from "@/lib/utils";
import { FLOW_TEXT, RESULTS, decisionFlow, deferral, entries, purposeLabel, type Explained } from "./explain";
import { agentLabel } from "./labels";

type Round = Schemas["CoordinationOut"];

const ALL = "all";

function amount(cost: Cost | undefined, kind: Resource): number {
  if (!cost) return 0;
  return kind === "clay" ? cost.clay ?? cost.stone ?? 0 : cost[kind] ?? 0;
}

function BudgetBars({ budget }: { budget?: Budget }) {
  const reservations = (budget?.reservations ?? []).filter((r) => Object.values(r.cost ?? {}).some((v) => (v ?? 0) > 0));
  const purposes = [...new Set(reservations.map((r) => r.purpose))];
  const tone = (purpose: string) => SHADES[(purposes.indexOf(purpose) + 1) % SHADES.length];
  const kinds = Object.keys(RESOURCES) as Resource[];
  const peak = Math.max(1, ...kinds.map((k) => amount(budget?.stock, k)));

  if (!budget?.stock) return <p className="text-[13px] text-secondary">Sem orçamento registrado nesta rodada.</p>;

  return (
    <div className="space-y-3">
      {kinds.map((kind) => {
        const stock = amount(budget.stock, kind);
        const free = amount(budget.free, kind);
        const parts = purposes.map((p) => ({ purpose: p, value: reservations.filter((r) => r.purpose === p).reduce((s, r) => s + amount(r.cost, kind), 0) })).filter((p) => p.value > 0);
        const held = parts.reduce((s, p) => s + p.value, 0);
        const summary = `${RESOURCES[kind].label}: estoque ${num(stock)}, reservado ${num(held)}, livre ${num(free)}`;
        return (
          <div key={kind}>
            <div className="mb-1 flex items-baseline justify-between gap-3 text-[13px]">
              <span className="text-secondary">{RESOURCES[kind].label}</span>
              <span className="font-mono text-[12px] tabular-nums">
                {num(free)} <span className="text-muted-foreground">livre de {num(stock)}</span>
              </span>
            </div>
            <div role="img" aria-label={summary} title={summary} className="flex h-3 overflow-hidden rounded-full bg-surface-hover" style={{ width: `${Math.max(4, (stock / peak) * 100)}%` }}>
              {parts.map((p) => (
                <div key={p.purpose} title={`${purposeLabel(p.purpose)}: ${num(p.value)}`} className={cn("h-full border-r border-background bg-current", tone(p.purpose))} style={{ width: `${stock ? (p.value / stock) * 100 : 0}%` }} />
              ))}
              <div className={cn("h-full bg-current", RESOURCES[kind].color)} style={{ width: `${stock ? (free / stock) * 100 : 0}%` }} />
            </div>
          </div>
        );
      })}
      <ul className="flex flex-wrap gap-x-4 gap-y-1.5 pt-1 text-[12px] text-secondary">
        {purposes.map((p) => (
          <li key={p} className="inline-flex items-center gap-1.5"><i aria-hidden className={cn("size-2 rounded-[2px] bg-current", tone(p))} />reservado: {purposeLabel(p)}</li>
        ))}
        <li className="inline-flex items-center gap-1.5"><i aria-hidden className="size-2 rounded-[2px] bg-wood" />livre para gastar (cor do recurso)</li>
      </ul>
    </div>
  );
}

function WhyNot({ items }: { items: (Explained & { village?: string })[] }) {
  if (items.length === 0) return <p className="px-4 py-6 text-center text-[13px] text-secondary">Nada ficou para depois nesta rodada.</p>;
  return (
    <PageScope total={items.length}>
      <ul className="divide-y divide-border-subtle">
        <PageSlice>{items.map((e, i) => {
          const d = deferral(e.why_kind);
          return (
            <li key={i} className="px-4 py-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{readable(e.title ?? e.action)}</span>
                <Badge tone="warning">{d.label}</Badge>
              </div>
              <p className="mt-1 text-[13px] text-secondary">
                {agentLabel(e.source)} propôs{e.village ? ` em ${e.village}` : ""}; não fez porque {d.plain}.
              </p>
              <p className="mt-0.5 text-[12px] text-muted-foreground">
                {readable(e.why)}
                {e.ready_in_hours != null && ` · pronta em ${duration(e.ready_in_hours * 3600)}`}
              </p>
            </li>
          );
        })}</PageSlice>
      </ul>
      <PageFooter noun={["proposta", "propostas"]} />
    </PageScope>
  );
}

function FlowTable({ rounds }: { rounds: Round[] }) {
  const rows = new Map<string, { ok: number; bad: number; later: number }>();
  for (const round of rounds) {
    const { executed, deferred } = entries(round);
    for (const e of executed) {
      const row = rows.get(e.source ?? "coordinator") ?? { ok: 0, bad: 0, later: 0 };
      if ((e.outcome ?? (e.ok ? "ok" : "failed")) === "ok") row.ok += 1;
      else row.bad += 1;
      rows.set(e.source ?? "coordinator", row);
    }
    for (const e of deferred) {
      const row = rows.get(e.source ?? "coordinator") ?? { ok: 0, bad: 0, later: 0 };
      row.later += 1;
      rows.set(e.source ?? "coordinator", row);
    }
  }
  const list = [...rows.entries()].sort((a, b) => b[1].ok + b[1].bad + b[1].later - (a[1].ok + a[1].bad + a[1].later));
  return (
    <Table>
      <thead><tr><Th>Especialista</Th><Th className="text-right">Feitas</Th><Th className="text-right">Recusadas ou com erro</Th><Th className="text-right">Adiadas</Th></tr></thead>
      <tbody>
        {list.map(([source, r]) => (
          <tr key={source}>
            <Td>{agentLabel(source)}</Td>
            <Td className="text-right font-mono tabular-nums">{num(r.ok)}</Td>
            <Td className="text-right font-mono tabular-nums">{num(r.bad)}</Td>
            <Td className="text-right font-mono tabular-nums">{num(r.later)}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function RoundExplain({ rounds }: { rounds: Round[] }) {
  const [pick, setPick] = useState(rounds.length > 1 ? ALL : String(rounds[0]?.village_id ?? ALL));
  const chosen = pick === ALL ? rounds : rounds.filter((r) => String(r.village_id) === pick);
  const flow = decisionFlow(chosen);
  const later = chosen.flatMap((r) => entries(r).deferred.map((e) => ({ ...e, village: rounds.length > 1 ? r.village : undefined })));
  const done = chosen.reduce((s, r) => s + entries(r).executed.filter((e) => (e.outcome ?? (e.ok ? "ok" : "")) === "ok").length, 0);
  const budgets = chosen.map((r) => ({ id: r.village_id, name: r.village, budget: entries(r).budget }));

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">Como o coordenador decidiu</h2>
          <p className="mt-0.5 text-[13px] text-secondary">Cada especialista propõe; o coordenador executa ou adia com um motivo; o jogo aceita, recusa ou dá erro.</p>
        </div>
        {rounds.length > 1 && (
          <Select
            aria-label="Aldeia"
            value={pick}
            onChange={setPick}
            options={[{ value: ALL, label: "Todas as aldeias" }, ...rounds.map((r) => ({ value: String(r.village_id), label: r.village || `Aldeia ${r.village_id}` }))]}
            className="w-full sm:w-72"
          />
        )}
      </div>

      <ChartCard
        title={<><GitFork className="size-4 text-secondary" strokeWidth={1.75} />Da proposta ao resultado</>}
        description={`${num(flow.calls)} propostas · ${num(done)} feitas · ${num(later.length)} adiadas`}
        legend={
          <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] text-secondary">
            {Object.entries(RESULTS).map(([id, r]) => (
              <li key={id} className="inline-flex items-center gap-1.5"><i aria-hidden className={cn("size-2 rounded-[2px] bg-current", r.tone)} />{r.label}</li>
            ))}
          </ul>
        }
        chart={<div className="overflow-x-auto"><div className="min-w-[320px]"><Sankey data={flow} text={FLOW_TEXT} /></div></div>}
        table={<FlowTable rounds={chosen} />}
      />

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <Panel>
          <PanelHeader title={<><CircleHelp className="size-4 text-secondary" strokeWidth={1.75} />Por que não fez</>} description="cada proposta adiada, com o motivo em linguagem simples" aside={<Badge tone={later.length ? "warning" : "neutral"}>{num(later.length)}</Badge>} />
          <WhyNot items={later} />
        </Panel>
        <Panel>
          <PanelHeader title={<><Wallet className="size-4 text-secondary" strokeWidth={1.75} />Orçamento da rodada</>} description="estoque dividido entre reservas e o que sobrou livre" />
          <div className="space-y-5 p-4">
            {budgets.map((b) => (
              <div key={b.id} className="space-y-2">
                {budgets.length > 1 && <div className="text-[13px] font-medium">{b.name}</div>}
                <BudgetBars budget={b.budget} />
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </section>
  );
}
