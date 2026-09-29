"use client";

import { Workflow } from "lucide-react";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Table, Td, Th } from "@/components/ui/table";
import { ChartCard } from "@/features/charts/parts";
import type { Schemas } from "@/lib/api";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";
import { agentLabel, OUTCOMES, outcomeLabel, toolLabel } from "./labels";
import { Sankey } from "./sankey";

type Flow = Schemas["FlowOut"];

function FlowTable({ data }: { data: Flow }) {
  const outcomes = data.outcomes.map((o) => o.id);
  const byTool = new Map<string, Record<string, number>>();
  for (const l of data.tool_outcome) byTool.set(l.source, { ...byTool.get(l.source), [l.target]: l.count });
  const rows = [...data.agent_tool].sort((a, b) => b.count - a.count);

  return (
    <div className="divide-y divide-border">
      <PageScope total={rows.length}>
      <Table>
        <thead><tr><Th>Agente</Th><Th>Ferramenta</Th><Th className="text-right">Chamadas</Th></tr></thead>
        <tbody>
          {rows.length === 0 && <tr><Td colSpan={3} className="text-secondary">Sem dados.</Td></tr>}
          <PageSlice>{rows.map((l) => (
            <tr key={`${l.source}:${l.target}`}>
              <Td>{agentLabel(l.source)}</Td>
              <Td className="text-secondary">{toolLabel(l.target)}</Td>
              <Td className="text-right font-mono tabular-nums">{num(l.count)}</Td>
            </tr>
          ))}</PageSlice>
        </tbody>
      </Table>
      <PageFooter noun={["ligação", "ligações"]} />
      </PageScope>
      <PageScope total={data.tools.length}>
      <Table>
        <thead>
          <tr>
            <Th>Ferramenta</Th>
            {outcomes.map((o) => <Th key={o} className="text-right whitespace-nowrap">{outcomeLabel(o)}</Th>)}
          </tr>
        </thead>
        <tbody>
          <PageSlice>{data.tools.map((t) => (
            <tr key={t.id}>
              <Td>{toolLabel(t.id)}</Td>
              {outcomes.map((o) => <Td key={o} className="text-right font-mono tabular-nums">{num(byTool.get(t.id)?.[o] ?? 0)}</Td>)}
            </tr>
          ))}</PageSlice>
        </tbody>
      </Table>
      <PageFooter noun={["ferramenta", "ferramentas"]} />
      </PageScope>
    </div>
  );
}

export function FlowView({ data }: { data: Flow }) {
  return (
    <ChartCard
      title={<><Workflow className="size-4 text-secondary" strokeWidth={1.75} />Grafo de decisões</>}
      description={`${num(data.calls)} chamadas de ferramenta em ${num(data.runs)} ${data.runs === 1 ? "rodada" : "rodadas"}`}
      legend={
        <div className="space-y-2">
          <p className="text-[13px] text-secondary">Cada faixa é uma chamada: do agente (esquerda) para a ferramenta (meio) e para o resultado (direita). Passe o mouse para destacar um caminho.</p>
          <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] text-secondary">
            {Object.entries(OUTCOMES).map(([id, o]) => (
              <li key={id} className="inline-flex items-center gap-1.5"><i aria-hidden className={cn("size-2 rounded-[2px]", o.fill)} />{o.label}</li>
            ))}
          </ul>
        </div>
      }
      chart={<div className="overflow-x-auto"><div className="min-w-[320px]"><Sankey data={data} /></div></div>}
      table={<FlowTable data={data} />}
    />
  );
}
