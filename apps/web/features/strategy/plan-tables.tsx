import { Check, Clock, Flag } from "lucide-react";
import type { ReactNode } from "react";
import { ActionButton } from "@/components/ui/action-button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Table, Td, Th } from "@/components/ui/table";
import { duration, num, percent } from "@/lib/format";
import { CostLine } from "./cost-line";
import { APPROVAL, HORIZON, type Entry } from "./types";

type Who = (key?: string) => string;

function Priority({ value }: { value?: number }) {
  return <span className="inline-flex h-6 min-w-9 items-center justify-center rounded-md border border-border-subtle bg-background px-1.5 font-mono text-[12px] tabular-nums">{value ?? "—"}</span>;
}

function MobileItem({ entry, who, children }: { entry: Entry; who: Who; children: ReactNode }) {
  return (
    <li className="flex items-start gap-3 px-4 py-3">
      <Priority value={entry.priority} />
      <div className="min-w-0 flex-1 text-sm">
        <div className="font-medium">{entry.title ?? entry.action}</div>
        <div className="text-[12px] text-secondary">{who(entry.source)}</div>
        {children}
      </div>
    </li>
  );
}

function Approve({ villageId, entry }: { villageId: number; entry: Entry }) {
  if (entry.why !== APPROVAL || !entry.action) return null;
  return (
    <ActionButton
      size="sm"
      path="/api/v1/agents/act"
      body={{ village_id: villageId, tool: entry.action, arguments: { ...(entry.arguments ?? {}), reason: "aprovado no painel" }, dry_run: false, source: "web" }}
      confirm={{ title: "Aprovar esta ação?", description: `Executar "${entry.title ?? entry.action}" agora no jogo.`, confirmLabel: "Executar" }}
      success="Aprovado"
      successField="detail"
    >
      <Check className="size-3.5" strokeWidth={2} />
      Aprovar
    </ActionButton>
  );
}

export function ExecutedTable({ entries, who }: { entries: Entry[]; who: Who }) {
  return (
    <Panel>
      <PanelHeader title={<><Flag className="size-4 text-secondary" strokeWidth={1.75} />Plano em sequência</>} description="executado nesta rodada, na ordem da prioridade" aside={<Badge>{num(entries.length)}</Badge>} />
      {entries.length === 0 ? (
        <EmptyState icon={Flag} title="Nada executado nesta rodada" />
      ) : (
        <PageScope total={entries.length}>
          <ol className="divide-y divide-border-subtle md:hidden">
            <PageSlice>{entries.map((e, i) => (
              <MobileItem key={i} entry={e} who={who}>
                <p className="mt-1 text-[13px] text-secondary">{e.reason}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                  <Badge tone={e.ok ? "success" : "danger"}>{e.ok ? "ok" : "falhou"}</Badge>
                  <span className="text-[12px] text-muted-foreground">confiança {percent(e.confidence)}</span>
                </div>
                {e.result && <p className="mt-1 text-[12px] text-muted-foreground">{e.result}</p>}
              </MobileItem>
            ))}</PageSlice>
          </ol>
          <div className="hidden md:block">
            <Table className="min-w-[760px]">
              <thead>
                <tr>
                  <Th className="w-16">Prior.</Th>
                  <Th>Ação</Th>
                  <Th>Quem propôs</Th>
                  <Th>Por quê</Th>
                  <Th className="text-right">Confiança</Th>
                  <Th>Resultado</Th>
                </tr>
              </thead>
              <tbody>
                <PageSlice>{entries.map((e, i) => (
                  <tr key={i}>
                    <Td><Priority value={e.priority} /></Td>
                    <Td className="font-medium">{e.title ?? e.action}<CostLine cost={e.cost} empty="" className="mt-1 block text-[12px] text-secondary" /></Td>
                    <Td className="whitespace-nowrap text-secondary">{who(e.source)}</Td>
                    <Td className="text-[13px] text-secondary">{e.reason}</Td>
                    <Td className="text-right tabular-nums">{percent(e.confidence)}</Td>
                    <Td className="max-w-[280px]">
                      <Badge tone={e.ok ? "success" : "danger"}>{e.ok ? "ok" : "falhou"}</Badge>
                      {e.result && <p className="mt-1 text-[12px] text-muted-foreground">{e.result}</p>}
                    </Td>
                  </tr>
                ))}</PageSlice>
              </tbody>
            </Table>
          </div>
          <PageFooter noun={["proposta", "propostas"]} />
        </PageScope>
      )}
    </Panel>
  );
}

export function DeferredTable({ entries, who, villageId }: { entries: Entry[]; who: Who; villageId: number }) {
  return (
    <Panel>
      <PanelHeader title={<><Clock className="size-4 text-secondary" strokeWidth={1.75} />Alertas e conflitos</>} description="propostas adiadas e o motivo" aside={<Badge tone={entries.length ? "warning" : "neutral"}>{num(entries.length)}</Badge>} />
      {entries.length === 0 ? (
        <EmptyState icon={Clock} title="Nenhuma proposta adiada" />
      ) : (
        <PageScope total={entries.length}>
          <ol className="divide-y divide-border-subtle md:hidden">
            <PageSlice>{entries.map((e, i) => (
              <MobileItem key={i} entry={e} who={who}>
                <p className="mt-1 text-[13px] text-status-warn">{e.why}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[12px] text-muted-foreground">
                  {e.horizon && <Badge>{HORIZON[e.horizon] ?? e.horizon}</Badge>}
                  {e.ready_in_hours != null && <span>pronta em {duration(e.ready_in_hours * 3600)}</span>}
                </div>
                <div className="mt-2 empty:hidden"><Approve villageId={villageId} entry={e} /></div>
              </MobileItem>
            ))}</PageSlice>
          </ol>
          <div className="hidden md:block">
            <Table className="min-w-[820px]">
              <thead>
                <tr>
                  <Th className="w-16">Prior.</Th>
                  <Th>Ação</Th>
                  <Th>Quem propôs</Th>
                  <Th>Adiada porque</Th>
                  <Th>Horizonte</Th>
                  <Th className="text-right">Pronta em</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                <PageSlice>{entries.map((e, i) => (
                  <tr key={i}>
                    <Td><Priority value={e.priority} /></Td>
                    <Td className="font-medium">{e.title ?? e.action}<CostLine cost={e.cost} empty="" className="mt-1 block text-[12px] text-secondary" /></Td>
                    <Td className="whitespace-nowrap text-secondary">{who(e.source)}</Td>
                    <Td className="text-[13px] text-status-warn">{e.why}</Td>
                    <Td className="whitespace-nowrap text-secondary">{e.horizon ? HORIZON[e.horizon] ?? e.horizon : "—"}</Td>
                    <Td className="whitespace-nowrap text-right font-mono text-[12px] tabular-nums">{e.ready_in_hours != null ? duration(e.ready_in_hours * 3600) : "—"}</Td>
                    <Td className="text-right"><Approve villageId={villageId} entry={e} /></Td>
                  </tr>
                ))}</PageSlice>
              </tbody>
            </Table>
          </div>
          <PageFooter noun={["proposta", "propostas"]} />
        </PageScope>
      )}
    </Panel>
  );
}
