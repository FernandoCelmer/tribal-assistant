import { Flag } from "lucide-react";
import { BuildingIcon, UnitIcon } from "@/components/game/icons";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Schemas } from "@/lib/api";
import { num, relative } from "@/lib/format";
import { BUILDINGS, UNITS } from "@/lib/game";

type Plan = Schemas["VillagePlanOut"];
type Step = Schemas["PlanStep"];

const STATES: Record<string, { label: string; tone: "neutral" | "warning" | "success" | "danger" }> = {
  pending: { label: "pendente", tone: "neutral" },
  queued: { label: "em andamento", tone: "warning" },
  done: { label: "feito", tone: "success" },
  blocked: { label: "bloqueado", tone: "danger" },
};

const SOURCES: Record<string, string> = { llm: "IA", rules: "regras" };

function label(step: Step): string {
  if (step.kind === "build") return `Construir ${BUILDINGS[step.target] ?? step.target} até o nível ${step.amount}`;
  if (step.kind === "recruit") return `Recrutar ${UNITS[step.target] ?? step.target} até ${num(step.amount)}`;
  return `Desbloquear coleta nível ${step.target}`;
}

function StepIcon({ step }: { step: Step }) {
  if (step.kind === "build") return <BuildingIcon name={step.target} level={step.amount} className="size-6" />;
  if (step.kind === "recruit") return <UnitIcon name={step.target} className="size-5" />;
  return <span className="flex size-6 items-center justify-center rounded-md border border-border-subtle font-mono text-[11px] text-secondary">{step.target}</span>;
}

function PlanCard({ plan }: { plan: Plan }) {
  const pct = plan.total ? Math.round((plan.done / plan.total) * 100) : 0;
  return (
    <article className="space-y-3">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-sm font-semibold">{plan.village}</span>
        <span className="text-[12px] text-secondary">feito por {SOURCES[plan.source] ?? plan.source} · {plan.refreshed_at ? `atualizado ${relative(plan.refreshed_at)}` : "—"}</span>
        <span className="ml-auto font-mono text-[12px] tabular-nums text-secondary">{plan.done}/{plan.total} passos</span>
      </header>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-hover" role="meter" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Progresso do plano">
        <div className="h-full rounded-full bg-status-ok" style={{ width: `${pct}%` }} />
      </div>
      {plan.summary && <p className="text-[13px] text-secondary">{plan.summary}</p>}
      <ol className="divide-y divide-border-subtle rounded-lg border border-border">
        {plan.steps.map((step, i) => {
          const state = STATES[step.status ?? "pending"] ?? { label: step.status ?? "", tone: "neutral" as const };
          return (
            <li key={i} className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-sm sm:flex-nowrap">
              <span className="w-5 shrink-0 text-right font-mono text-[11px] text-muted-foreground">{i + 1}</span>
              <StepIcon step={step} />
              <span className={step.status === "done" ? "min-w-0 flex-1 text-secondary line-through decoration-border-hover" : "min-w-0 flex-1"}>
                {label(step)}
                {step.reason && <span className="block text-[12px] text-muted-foreground">{step.reason}</span>}
              </span>
              <span className="flex shrink-0 flex-col items-end gap-0.5">
                <Badge tone={state.tone}>{state.label}</Badge>
                {step.note && <span className="max-w-[240px] truncate text-[11px] text-muted-foreground">{step.note}</span>}
              </span>
            </li>
          );
        })}
      </ol>
    </article>
  );
}

export function VillagePlans({ plans }: { plans: Plan[] }) {
  const visible = plans.filter((p) => p.total > 0);
  return (
    <Panel>
      <PanelHeader title={<><Flag className="size-4 text-secondary" strokeWidth={1.75} />Plano da aldeia</>} description="escrito pelo Estrategista, executado pelos outros agentes" />
      {visible.length === 0 ? (
        <EmptyState icon={Flag} title="Ainda não há plano" text="O Estrategista cria um na próxima rodada." />
      ) : (
        <PageScope total={visible.length} per={10}>
          <div className="space-y-6 p-4"><PageSlice>{visible.map((p) => <PlanCard key={p.village_id} plan={p} />)}</PageSlice></div>
          <PageFooter noun={["plano", "planos"]} />
        </PageScope>
      )}
    </Panel>
  );
}
