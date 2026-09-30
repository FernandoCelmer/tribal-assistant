import { readable } from "@/features/flow/labels";
import { BookOpen, Crown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Table, Td, Th } from "@/components/ui/table";
import { AgentMark } from "@/features/agents/agent-mark";
import type { Schemas } from "@/lib/api";
import { duration, num, percent } from "@/lib/format";
import { CERTAINTY, type Insight } from "./types";

type Proposer = Schemas["ProposerOut"];

function Certainty({ value }: { value: string }) {
  const c = CERTAINTY[value] ?? { label: value, tone: "neutral" as const };
  return <Badge tone={c.tone}>{c.label}</Badge>;
}

export function InsightsTable({ insights }: { insights: Insight[] }) {
  const sorted = [...insights].sort((a, b) => b.weight - a.weight);
  return (
    <Panel>
      <PanelHeader title={<><BookOpen className="size-4 text-secondary" strokeWidth={1.75} />O que sabemos</>} description="fato, estimativa ou hipótese, com idade e peso" aside={<Badge>{num(insights.length)}</Badge>} />
      {sorted.length === 0 ? (
        <EmptyState icon={BookOpen} title="Sem informações" />
      ) : (
        <PageScope total={sorted.length}>
        <Table>
          <thead>
            <tr>
              <Th className="w-24">Tipo</Th>
              <Th>Informação</Th>
              <Th className="text-right">Idade</Th>
              <Th className="text-right">Peso</Th>
            </tr>
          </thead>
          <tbody>
            <PageSlice>{sorted.map((i, n) => (
              <tr key={i.key ?? n}>
                <Td><Certainty value={i.certainty} /></Td>
                <Td className="min-w-[180px] text-[13px]">{readable(i.text)}</Td>
                <Td className="whitespace-nowrap text-right font-mono text-[12px] tabular-nums text-secondary">{duration(i.age_hours * 3600)}</Td>
                <Td className="text-right">
                  <span className="inline-flex items-center gap-2">
                    <span className="hidden h-1 w-10 overflow-hidden rounded-full bg-surface-hover sm:block"><span className="block h-full bg-foreground" style={{ width: percent(i.weight) }} /></span>
                    <span className="font-mono text-[12px] tabular-nums">{percent(i.weight)}</span>
                  </span>
                </Td>
              </tr>
            ))}</PageSlice>
          </tbody>
        </Table>
        <PageFooter noun={["informação", "informações"]} />
        </PageScope>
      )}
    </Panel>
  );
}

export function SpecialistsTable({ proposers }: { proposers: Proposer[] }) {
  return (
    <Panel>
      <PanelHeader title={<><Crown className="size-4 text-secondary" strokeWidth={1.75} />Especialistas</>} description="quem propõe, o que observa e o que entrega" aside={<Badge>{num(proposers.length)}</Badge>} />
      {proposers.length === 0 ? (
        <EmptyState icon={Crown} title="Nenhum especialista registrado" />
      ) : (
        <PageScope total={proposers.length}>
        <ul className="divide-y divide-border-subtle">
          <PageSlice>{proposers.map((p) => (
            <li key={p.key} className="flex items-start gap-3 px-4 py-3">
              <AgentMark agent={p.key} />
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium">{p.title}</div>
                <dl className="mt-1 grid grid-cols-1 gap-1 text-[13px] sm:grid-cols-[72px_minmax(0,1fr)] sm:gap-x-3">
                  <dt className="text-[11px] uppercase tracking-wide text-muted-foreground sm:pt-0.5">Observa</dt>
                  <dd className="text-secondary">{p.observes}</dd>
                  <dt className="text-[11px] uppercase tracking-wide text-muted-foreground sm:pt-0.5">Entrega</dt>
                  <dd className="text-secondary">{p.delivers}</dd>
                </dl>
              </div>
            </li>
          ))}</PageSlice>
        </ul>
        <PageFooter noun={["especialista", "especialistas"]} />
        </PageScope>
      )}
    </Panel>
  );
}
