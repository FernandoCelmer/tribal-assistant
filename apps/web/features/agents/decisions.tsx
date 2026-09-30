import { Gavel } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Schemas } from "@/lib/api";
import { num, short } from "@/lib/format";
import { AgentMark } from "./agent-mark";
import { toolLabel } from "@/features/flow/labels";
import { agentLabel } from "./labels";

type Decision = Schemas["DecisionOut"];

function args(value: Record<string, unknown>): string {
  return Object.entries(value)
    .filter(([k]) => k !== "reason")
    .map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(" · ");
}

export function Decisions({ decisions, villages }: { decisions: Decision[]; villages: Record<string, string> }) {
  const refusedCount = decisions.filter((d) => !d.ok && d.result.startsWith("RECUSADO")).length;
  return (
    <Panel>
      <PanelHeader title={<><Gavel className="size-4 text-secondary" strokeWidth={1.75} />Decisões</>} description="ações que os agentes tentaram nesta rodada" aside={<Badge>{num(decisions.length)}{refusedCount ? ` · ${refusedCount} recusadas` : ""}</Badge>} />
      {decisions.length === 0 ? (
        <EmptyState icon={Gavel} title="Nenhuma ação tentada" />
      ) : (
        <PageScope total={decisions.length}>
        <ul className="divide-y divide-border-subtle">
          <PageSlice>{decisions.map((d) => {
            const refused = !d.ok && d.result.startsWith("RECUSADO");
            return (
              <li key={d.id} className="flex items-start gap-3 px-4 py-3">
                <AgentMark agent={d.agent} size="sm" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                    <span className="font-medium">{toolLabel(d.action)}</span>
                    <span className="text-[12px] text-secondary">{agentLabel(d.agent)}{d.village_id != null && ` · ${villages[String(d.village_id)] ?? d.village_id}`}</span>
                    {d.dry_run && <Badge>simulação</Badge>}
                  </div>
                  {args(d.arguments) && <div className="mt-0.5 truncate font-mono text-[12px] text-muted-foreground">{args(d.arguments)}</div>}
                  {d.reason && <p className="mt-1 text-[13px] text-secondary">{d.reason}</p>}
                  {d.result && <p className={refused ? "mt-1 text-[13px] text-status-warn" : d.ok ? "mt-1 text-[13px] text-foreground" : "mt-1 text-[13px] text-status-bad"}>{d.result}</p>}
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <Badge tone={d.ok ? "success" : refused ? "warning" : "danger"}>{d.ok ? "ok" : refused ? "recusada" : "falhou"}</Badge>
                  <span className="font-mono text-[11px] text-muted-foreground">{short(d.created_at)}</span>
                </div>
              </li>
            );
          })}</PageSlice>
        </ul>
        <PageFooter noun={["decisão", "decisões"]} />
        </PageScope>
      )}
    </Panel>
  );
}
