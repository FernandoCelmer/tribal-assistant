"use client";

import { ChartNoAxesColumn, Hourglass } from "lucide-react";
import Link from "next/link";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Block } from "@/components/ui/skeleton";
import { Table, Td, Th } from "@/components/ui/table";
import { BarList } from "@/features/charts/bar-list";
import { ChartCard, Legend } from "@/features/charts/parts";
import { stamp, type Series } from "@/features/charts/scale";
import { StackedBars } from "@/features/charts/stacked-bars";
import { useMounted } from "@/features/charts/use-width";
import type { Schemas } from "@/lib/api";
import { num, utc } from "@/lib/format";
import { DEFERRALS, GROUPS, RESULTS } from "./explain";

type Summary = Schemas["RoundSummaryOut"];

function grouped(row: Summary, group: string): number {
  return Object.entries(row.deferred).reduce((s, [kind, n]) => s + ((DEFERRALS[kind] ?? DEFERRALS.learned).group === group ? n : 0), 0);
}

export function DecisionTimeline({ history }: { history: Summary[] }) {
  const mounted = useMounted();
  if (!mounted) return <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]"><Block className="h-[330px]" /><Block className="h-[330px]" /></div>;

  const at = history.map((h) => utc(h.created_at));
  const series: Series[] = [
    { key: "ok", label: RESULTS.ok.label, tone: RESULTS.ok.tone, values: history.map((h) => h.executed) },
    { key: "refused", label: RESULTS.refused.label, tone: RESULTS.refused.tone, values: history.map((h) => h.refused) },
    { key: "failed", label: RESULTS.failed.label, tone: RESULTS.failed.tone, values: history.map((h) => h.failed) },
    ...GROUPS.map((g) => ({ key: g.id, label: `adiada: ${g.label}`, tone: g.tone, values: history.map((h) => grouped(h, g.id)) })),
  ].filter((s) => s.values.some(Boolean));
  const totals = new Map<string, number>();
  for (const h of history) for (const [kind, n] of Object.entries(h.deferred)) totals.set(kind, (totals.get(kind) ?? 0) + n);
  const blockers = [...totals.entries()].map(([label, count]) => ({ label, count }));
  const rows = history.toReversed();

  return (
    <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
      <ChartCard
        title={<><ChartNoAxesColumn className="size-4 text-secondary" strokeWidth={1.75} />Decisões por rodada</>}
        description={`últimas ${num(history.length)} rodadas do coordenador: o que saiu e o que ficou para depois`}
        legend={<Legend items={series} />}
        chart={<StackedBars labels={at.map((d) => d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }))} titles={at.map(stamp)} series={series} label="Propostas feitas e adiadas por rodada" empty="Nenhuma rodada do coordenador ainda." />}
        table={
          <PageScope total={rows.length}>
            <Table>
              <thead><tr><Th>Rodada</Th><Th className="text-right">Feitas</Th><Th className="text-right">Recusadas</Th><Th className="text-right">Erros</Th><Th className="text-right">Adiadas</Th></tr></thead>
              <tbody>
                <PageSlice>{rows.map((h) => (
                  <tr key={h.run_id}>
                    <Td><Link href={`/agents/${h.run_id}`} className="font-mono text-[13px] underline-offset-4 hover:underline">{stamp(utc(h.created_at))}</Link></Td>
                    <Td className="text-right font-mono tabular-nums">{num(h.executed)}</Td>
                    <Td className="text-right font-mono tabular-nums">{num(h.refused)}</Td>
                    <Td className="text-right font-mono tabular-nums">{num(h.failed)}</Td>
                    <Td className="text-right font-mono tabular-nums">{num(Object.values(h.deferred).reduce((s, n) => s + n, 0))}</Td>
                  </tr>
                ))}</PageSlice>
              </tbody>
            </Table>
            <PageFooter noun={["rodada", "rodadas"]} />
          </PageScope>
        }
      />
      <ChartCard
        title={<><Hourglass className="size-4 text-secondary" strokeWidth={1.75} />O que mais trava</>}
        description="motivos das propostas adiadas nessas rodadas"
        chart={<BarList rows={blockers} labelOf={(k) => (DEFERRALS[k] ?? DEFERRALS.learned).label} empty="Nada adiado nessas rodadas." tone="bg-status-warn/70" />}
      />
    </div>
  );
}
