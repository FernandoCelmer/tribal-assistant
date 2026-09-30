import { readable } from "@/features/flow/labels";
import { Sparkles, Star } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { percent } from "@/lib/format";
import { CostLine } from "./cost-line";
import { HORIZON, type Entry } from "./types";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[88px_minmax(0,1fr)] gap-3 py-2 text-sm">
      <dt className="text-[13px] text-secondary">{label}</dt>
      <dd className="min-w-0">{children}</dd>
    </div>
  );
}

export function NextAction({ entry, who }: { entry: Entry | null | undefined; who: (key?: string) => string }) {
  return (
    <Panel>
      <PanelHeader title={<><Star className="size-4 text-secondary" strokeWidth={1.75} />Próxima melhor ação</>} aside={entry?.horizon && <Badge>{HORIZON[entry.horizon] ?? entry.horizon}</Badge>} />
      {!entry ? (
        <EmptyState icon={Sparkles} title="Nada a fazer nesta rodada" text="O coordenador não encontrou proposta pendente." />
      ) : (
        <PanelBody>
          <div className="flex flex-wrap items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="text-lg font-semibold leading-6">{readable(entry.title ?? entry.action)}</div>
              <div className="mt-1 text-[13px] text-secondary">proposta por {who(entry.source)}</div>
            </div>
            {entry.why ? <Badge tone="warning">adiada</Badge> : entry.ok === false ? <Badge tone="danger">falhou</Badge> : entry.ok ? <Badge tone="success">executada</Badge> : null}
          </div>
          <dl className="mt-4 divide-y divide-border-subtle border-t border-border-subtle">
            <Row label="Por quê">{readable(entry.reason) || "—"}</Row>
            {entry.expected_benefit && <Row label="Impacto">{readable(entry.expected_benefit)}</Row>}
            <Row label="Custo"><CostLine cost={entry.cost} /></Row>
            <Row label="Confiança">
              <span className="inline-flex items-center gap-3">
                <span className="tabular-nums">{percent(entry.confidence)}</span>
                <span className="h-1.5 w-24 overflow-hidden rounded-full bg-surface-hover"><span className="block h-full rounded-full bg-foreground" style={{ width: percent(entry.confidence ?? 0) }} /></span>
                <span className="text-[13px] text-secondary">prioridade <span className="font-mono tabular-nums text-foreground">{entry.priority ?? "—"}</span></span>
              </span>
            </Row>
            {entry.why ? <Row label="Adiada"><span className="text-status-warn">{readable(entry.why)}</span></Row> : entry.result ? <Row label="Resultado">{readable(entry.result)}</Row> : null}
            {!!entry.risks?.length && <Row label="Riscos"><span className="text-secondary">{readable(entry.risks.join("; "))}</span></Row>}
          </dl>
        </PanelBody>
      )}
    </Panel>
  );
}
