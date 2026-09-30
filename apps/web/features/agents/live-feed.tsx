"use client";

import { toolLabel } from "@/features/flow/labels";
import { Activity, Eraser } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { short } from "@/lib/format";
import { cn } from "@/lib/utils";
import { AgentMark } from "./agent-mark";
import { STREAM_LABEL, useEvents, type StreamEvent } from "./events";
import { KIND_LABELS, TRIGGERS, agentLabel } from "./labels";

type FeedEvent = Exclude<StreamEvent, { kind: "sync" } | { kind: "decision" } | { kind: "flow" } | { kind: "micro" }>;
type Item = { id: number; event: FeedEvent };

const LIMIT = 200;

export function levelTone(level: string): "neutral" | "success" | "warning" | "danger" {
  if (level === "ERROR" || level === "CRITICAL") return "danger";
  if (level === "WARNING") return "warning";
  if (level === "SUCCESS") return "success";
  return "neutral";
}

function Line({ event }: { event: FeedEvent }) {
  if (event.kind === "run_started" || event.kind === "run_finished") {
    const d = event.data;
    const failed = event.kind === "run_finished" && d.status === "failed";
    return (
      <div className="min-w-0 flex-1 text-sm">
        <Link href={`/agents/${d.run_id}`} className="font-medium underline-offset-4 hover:underline">
          Rodada {d.run_id} {event.kind === "run_started" ? "começou" : failed ? "falhou" : "terminou"}
        </Link>
        <div className="truncate text-[12px] text-secondary">
          {event.kind === "run_started"
            ? `${TRIGGERS[d.trigger] ?? d.trigger} · ${d.brain === "llm" ? d.model ?? "IA" : "regras"}${d.dry_run ? " · simulação" : ""}`
            : `${d.actions_ok} feitas · ${d.actions_refused} recusadas · ${d.actions_failed} falhas${d.error ? ` · ${d.error}` : ""}`}
        </div>
      </div>
    );
  }
  if (event.kind === "log") {
    const d = event.data;
    return (
      <div className="flex min-w-0 flex-1 items-start gap-2 text-[13px]">
        <Badge tone={levelTone(d.level)} className="shrink-0">{d.level.toLowerCase()}</Badge>
        <span className="min-w-0 break-words text-secondary">{d.message}</span>
      </div>
    );
  }
  const d = event.data;
  const text = d.content.length > 220 ? `${d.content.slice(0, 219)}…` : d.content;
  return (
    <div className="min-w-0 flex-1 text-sm">
      <div className="flex flex-wrap items-center gap-x-2">
        <span className="font-medium">{agentLabel(d.agent)}</span>
        <span className="text-[12px] text-secondary">{KIND_LABELS[d.kind] ?? d.kind}{d.tool && <span title={d.tool}> {toolLabel(d.tool)}</span>}</span>
        {d.village && <span className="text-[12px] text-muted-foreground">· {d.village}</span>}
      </div>
      <p className={cn("mt-0.5 break-words text-[13px]", d.is_error ? "text-status-bad" : "text-secondary")}>{text}</p>
    </div>
  );
}

export function LiveFeed() {
  const [items, setItems] = useState<Item[]>([]);
  const [logs, setLogs] = useState(false);

  const state = useEvents((event) => {
    if (event.kind === "log" && !logs) return;
    if (event.kind === "sync" || event.kind === "decision" || event.kind === "flow" || event.kind === "micro") return;
    setItems((list) => [{ id: Date.now() + Math.random(), event }, ...list].slice(0, LIMIT));
  });

  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title={<><Activity className="size-4 text-secondary" strokeWidth={1.75} />Ao vivo</>}
        aside={
          <div className="flex items-center gap-2">
            <Badge tone={state === "live" ? "success" : state === "retrying" ? "warning" : "neutral"}>{STREAM_LABEL[state]}</Badge>
            <label className="inline-flex cursor-pointer items-center gap-1.5 text-[12px] text-secondary">
              <input type="checkbox" checked={logs} onChange={(e) => setLogs(e.target.checked)} className="size-3.5 accent-foreground" />
              logs
            </label>
            <Button size="icon" variant="ghost" aria-label="Limpar" onClick={() => setItems([])}><Eraser className="size-3.5" strokeWidth={1.75} /></Button>
          </div>
        }
      />
      {items.length === 0 ? (
        <EmptyState icon={Activity} title="Aguardando eventos" text="Passos, rodadas e logs aparecem aqui no instante em que acontecem." />
      ) : (
        <PageScope total={items.length} per={25}>
        <ol aria-live="polite" className="max-h-[560px] divide-y divide-border-subtle overflow-y-auto">
          <PageSlice>{items.map(({ id, event }) => (
            <li key={id} className="select-in flex items-start gap-3 px-4 py-2.5">
              {event.kind === "step" ? <AgentMark agent={event.data.agent} size="sm" /> : <span className="size-6 shrink-0" />}
              <Line event={event} />
              <span className="shrink-0 font-mono text-[11px] text-muted-foreground" suppressHydrationWarning>{short(event.data.at)}</span>
            </li>
          ))}</PageSlice>
        </ol>
        <PageFooter noun={["evento", "eventos"]} />
        </PageScope>
      )}
    </Panel>
  );
}
