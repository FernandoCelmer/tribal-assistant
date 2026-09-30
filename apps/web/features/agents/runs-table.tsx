import { ChevronRight, History } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Table, Td, Th } from "@/components/ui/table";
import type { Schemas } from "@/lib/api";
import { duration, num, short, utc } from "@/lib/format";
import { TRIGGERS, brainLabel, runStatus } from "./labels";

type Run = Schemas["RunOut"];

export function runSeconds(run: Pick<Run, "started_at" | "finished_at">, now = Date.now()): number {
  const end = run.finished_at ? utc(run.finished_at).getTime() : now;
  return (end - utc(run.started_at).getTime()) / 1000;
}

function ModeBadge({ dry }: { dry: boolean }) {
  return dry ? <Badge>simulação</Badge> : <Badge tone="warning">ao vivo</Badge>;
}

export function RunsTable({ runs }: { runs: Run[] }) {
  return (
    <Panel>
      <PanelHeader title={<><History className="size-4 text-secondary" strokeWidth={1.75} />Rodadas</>} description="clique para ver o raciocínio completo" aside={<Badge>{num(runs.length)}</Badge>} />
      {runs.length === 0 ? (
        <EmptyState icon={History} title="Nenhuma rodada ainda" text="Clique em “Simular rodada” para ver os agentes pensando sem tocar no jogo." />
      ) : (
        <PageScope total={runs.length}>
          <ul className="divide-y divide-border-subtle md:hidden">
            <PageSlice>{runs.map((r) => {
              const status = runStatus(r.status);
              return (
                <li key={r.run_id}>
                  <Link href={`/agents/${r.run_id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-surface-hover">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 text-sm">
                        <span className="font-medium">{short(r.started_at)}</span>
                        <Badge tone={status.tone}>{status.label}</Badge>
                        <ModeBadge dry={r.dry_run} />
                      </div>
                      <div className="mt-1 truncate text-[12px] text-secondary">
                        {TRIGGERS[r.trigger] ?? r.trigger} · {brainLabel(r)} · {duration(runSeconds(r))} · {r.actions_ok} feitas · {r.actions_refused} recusadas · {r.actions_failed} falhas
                      </div>
                    </div>
                    <ChevronRight className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
                  </Link>
                </li>
              );
            })}</PageSlice>
          </ul>
          <div className="hidden md:block">
            <Table className="min-w-[760px]">
              <thead>
                <tr>
                  <Th>Início</Th>
                  <Th>Origem</Th>
                  <Th>Cérebro</Th>
                  <Th>Modo</Th>
                  <Th className="text-right">Duração</Th>
                  <Th className="text-right">Feitas</Th>
                  <Th className="text-right">Recusadas</Th>
                  <Th className="text-right">Falhas</Th>
                  <Th className="text-right">Tokens</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                <PageSlice>{runs.map((r) => {
                  const status = runStatus(r.status);
                  return (
                    <tr key={r.run_id} className="group hover:bg-surface-hover">
                      <Td className="align-middle whitespace-nowrap">
                        <Link href={`/agents/${r.run_id}`} className="font-medium underline-offset-4 group-hover:underline">{short(r.started_at)}</Link>
                      </Td>
                      <Td className="align-middle text-secondary">{TRIGGERS[r.trigger] ?? r.trigger}</Td>
                      <Td className="max-w-[160px] truncate align-middle font-mono text-[12px] text-secondary">{brainLabel(r)}</Td>
                      <Td className="align-middle"><ModeBadge dry={r.dry_run} /></Td>
                      <Td className="text-right align-middle font-mono text-[12px] tabular-nums">{duration(runSeconds(r))}</Td>
                      <Td className="text-right align-middle tabular-nums">{num(r.actions_ok)}</Td>
                      <Td className="text-right align-middle tabular-nums">{num(r.actions_refused)}</Td>
                      <Td className={r.actions_failed ? "text-right align-middle tabular-nums text-status-bad" : "text-right align-middle tabular-nums"}>{num(r.actions_failed)}</Td>
                      <Td className="text-right align-middle font-mono text-[12px] tabular-nums text-secondary">{num(r.tokens_in + r.tokens_out)}</Td>
                      <Td className="align-middle"><Badge tone={status.tone} title={r.error ?? undefined}>{status.label}</Badge></Td>
                    </tr>
                  );
                })}</PageSlice>
              </tbody>
            </Table>
          </div>
          <PageFooter noun={["rodada", "rodadas"]} />
        </PageScope>
      )}
    </Panel>
  );
}
