"use client";

import { readable, toolLabel } from "@/features/flow/labels";
import { Castle, ScrollText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Pager, usePaged } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { SegmentedControl } from "@/components/ui/segmented";
import type { Schemas } from "@/lib/api";
import { num, short } from "@/lib/format";
import { cn } from "@/lib/utils";
import { AgentMark } from "./agent-mark";
import { useEvents } from "./events";
import { KIND_LABELS, agentLabel, refused } from "./labels";

type Detail = Schemas["RunDetailOut"];
type Step = Schemas["StepOut"];
type Filter = "all" | "actions" | "thought" | "errors";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "Tudo" },
  { id: "actions", label: "Ações" },
  { id: "thought", label: "Raciocínio" },
  { id: "errors", label: "Erros" },
];

function keep(step: Step, filter: Filter): boolean {
  if (filter === "actions") return ["tool_call", "tool_result", "summary"].includes(step.kind);
  if (filter === "thought") return ["thought", "summary", "prompt"].includes(step.kind);
  if (filter === "errors") return step.is_error || refused(step) || step.kind === "error";
  return true;
}

type Group = { key: string; village: string; agent: string; steps: Step[] };

function group(steps: Step[], villages: Record<string, string>): Group[] {
  const out: Group[] = [];
  for (const step of steps) {
    const village = step.village_id != null ? villages[String(step.village_id)] ?? `aldeia ${step.village_id}` : "Rodada";
    const key = `${village}|${step.agent}`;
    const last = out[out.length - 1];
    if (last && last.key === key) last.steps.push(step);
    else out.push({ key, village, agent: step.agent, steps: [step] });
  }
  return out;
}

function pretty(content: string): string {
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return content;
  }
}

function Code({ children }: { children: string }) {
  return <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-md border border-border-subtle bg-background p-3 font-mono text-[12px] leading-5 text-secondary">{children}</pre>;
}

function Body({ step }: { step: Step }) {
  if (step.kind === "tool_call") return <Code>{pretty(step.content)}</Code>;
  if (step.kind === "prompt" || (step.kind === "tool_result" && step.content.length > 400)) {
    return (
      <details className="group mt-1">
        <summary className="cursor-pointer text-[13px] text-secondary hover:text-foreground">
          {step.kind === "prompt" ? "ver contexto completo enviado ao modelo" : `ver resposta completa (${num(step.content.length)} caracteres)`}
        </summary>
        <Code>{step.content}</Code>
      </details>
    );
  }
  return <p className={cn("mt-1 whitespace-pre-wrap break-words text-[13px] leading-5", step.is_error && !refused(step) ? "text-status-bad" : "text-secondary", step.kind === "summary" && "text-foreground")}>{readable(step.content)}</p>;
}

function StepItem({ step }: { step: Step }) {
  const isRefused = refused(step);
  return (
    <li className="relative pl-5">
      <span
        aria-hidden
        className={cn(
          "absolute left-0 top-[7px] size-2 rounded-full border",
          step.is_error && !isRefused ? "border-status-bad bg-status-bad" : isRefused ? "border-status-warn bg-status-warn" : step.kind === "summary" ? "border-foreground bg-foreground" : "border-border-hover bg-background",
        )}
      />
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[12px] font-medium uppercase tracking-wide text-muted-foreground">{KIND_LABELS[step.kind] ?? step.kind}</span>
        {step.tool && <span title={step.tool} className="rounded border border-border-subtle bg-background px-1.5 text-[12px]">{toolLabel(step.tool)}</span>}
        {isRefused ? <Badge tone="warning">recusado pela trava</Badge> : step.is_error ? <Badge tone="danger">erro</Badge> : null}
        <span className="ml-auto font-mono text-[11px] text-muted-foreground" suppressHydrationWarning>{short(step.created_at)}</span>
      </div>
      <Body step={step} />
    </li>
  );
}

export function RunTrace({ detail }: { detail: Detail }) {
  const router = useRouter();
  const [filter, setFilter] = useState<Filter>("all");
  const [steps, setSteps] = useState<Step[]>(detail.steps);
  const runId = detail.run.run_id;
  const running = detail.run.status === "running";

  useEffect(() => setSteps(detail.steps), [detail.steps]);

  useEvents((e) => {
    if (e.kind === "step" && e.data.run_id === runId) {
      setSteps((list) => (list.some((s) => s.seq === e.data.seq) ? list : [...list, { seq: e.data.seq, village_id: null, agent: e.data.agent, kind: e.data.kind, tool: e.data.tool, content: e.data.content, is_error: e.data.is_error, created_at: e.data.at }]));
    }
    if (e.kind === "run_finished" && e.data.run_id === runId) router.refresh();
  }, running);

  const groups = useMemo(() => group(steps, detail.villages).map((g) => ({ ...g, steps: g.steps.filter((s) => keep(s, filter)) })).filter((g) => g.steps.length), [steps, detail.villages, filter]);

  const paged = usePaged(groups);
  let lastVillage: string | null = null;

  return (
    <Panel>
      <PanelHeader
        title={<><ScrollText className="size-4 text-secondary" strokeWidth={1.75} />Raciocínio da rodada</>}
        description={`${num(steps.length)} passos${running ? " · recebendo ao vivo" : ""}`}
        aside={<SegmentedControl label="Filtrar passos" value={filter} options={FILTERS} onChange={setFilter} className="h-9 w-full sm:w-[360px]" />}
      />
      {groups.length === 0 ? (
        <EmptyState icon={ScrollText} title={steps.length ? "Nenhum passo com esse filtro" : "Sem passos registrados"} />
      ) : (
        <>
        <div className="space-y-6 p-4">
          {paged.rows.map((g, i) => {
            const head = g.village !== lastVillage;
            lastVillage = g.village;
            return (
              <div key={`${g.key}-${i}`}>
                {head && (
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                    <Castle className="size-4 text-secondary" strokeWidth={1.75} />
                    {g.village}
                  </h3>
                )}
                <section className="relative pl-10">
                  <span aria-hidden className="absolute left-[15px] top-8 bottom-0 w-px bg-border" />
                  <div className="absolute left-0 top-0"><AgentMark agent={g.agent} /></div>
                  <div className="flex min-h-8 items-center text-sm font-medium">{agentLabel(g.agent)}<span className="ml-2 text-[12px] font-normal text-muted-foreground">{g.steps.length} passos</span></div>
                  <ol className="mt-2 space-y-4 border-l border-transparent">{g.steps.map((s) => <StepItem key={s.seq} step={s} />)}</ol>
                </section>
              </div>
            );
          })}
        </div>
        <Pager paging={paged} noun={["bloco", "blocos"]} />
        </>
      )}
    </Panel>
  );
}
