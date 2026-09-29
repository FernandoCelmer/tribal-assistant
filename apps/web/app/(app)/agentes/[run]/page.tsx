import { ArrowLeft, CircleCheck, CircleX, Clock, Cpu, ShieldBan, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PageHeader } from "@/components/layout/page";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Stat } from "@/components/ui/stat";
import { Decisions, RunTrace, TRIGGERS, brainLabel, runSeconds, runStatus } from "@/features/agents";
import { maybe, server } from "@/lib/api";
import { duration, num, when } from "@/lib/format";

export default async function RunPage({ params }: { params: Promise<{ run: string }> }) {
  const { run: runId } = await params;
  const detail = await maybe(server.GET("/api/v1/agents/runs/{run_id}", { params: { path: { run_id: runId } } }));
  if (!detail) notFound();

  const run = detail.run;
  const status = runStatus(run.status);

  return (
    <div className="space-y-6">
      <Link href="/agentes" className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-foreground">
        <ArrowLeft className="size-3.5" strokeWidth={1.75} />
        Agentes
      </Link>

      <PageHeader
        title={`Rodada ${run.run_id}`}
        badge={<Badge tone={status.tone}>{status.label}</Badge>}
        description={`${TRIGGERS[run.trigger] ?? run.trigger} · ${run.brain === "llm" ? `${run.provider ?? ""} ${run.model ?? ""}`.trim() : "regras"} · ${run.dry_run ? "simulação" : "ao vivo"} · ${when(run.started_at)}`}
        actions={<Link href="/logs" className={buttonVariants({ variant: "outline" })}>Ver logs</Link>}
      />

      {run.error && (
        <div className="flex items-start gap-2 rounded-lg border border-status-bad/30 bg-status-bad/10 px-4 py-3 text-sm text-status-bad">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} />
          <span className="min-w-0 break-words">{run.error}</span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Duração" value={duration(runSeconds(run))} icon={Clock} hint={`${num(run.villages)} aldeias`} />
        <Stat label="Feitas" value={num(run.actions_ok)} icon={CircleCheck} />
        <Stat label="Recusadas" value={num(run.actions_refused)} icon={ShieldBan} tone={run.actions_refused ? "warn" : undefined} />
        <Stat label="Falhas" value={num(run.actions_failed)} icon={CircleX} tone={run.actions_failed ? "bad" : undefined} />
        <Stat label="Tokens" value={num(run.tokens_in + run.tokens_out)} icon={Cpu} hint={`${brainLabel(run)} · ${num(run.tokens_in)} in · ${num(run.tokens_out)} out`} className="col-span-2 lg:col-span-1" />
      </div>

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <RunTrace detail={detail} />
        <Decisions decisions={detail.decisions} villages={detail.villages} />
      </div>
    </div>
  );
}
