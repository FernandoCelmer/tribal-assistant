"use client";

import { Radio } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { Schemas } from "@/lib/api";
import { relative } from "@/lib/format";
import { cn } from "@/lib/utils";
import { STREAM_LABEL, useEvents } from "./events";
import { KIND_LABELS, agentLabel } from "./labels";

type Live = Schemas["LiveOut"];

export function LiveStatus({ initial, brain }: { initial: Live | null; brain: string }) {
  const router = useRouter();
  const [live, setLive] = useState<Live | null>(initial);

  const load = useCallback(async () => {
    try {
      const response = await fetch("/api/v1/agents/live", { cache: "no-store" });
      if (response.ok) setLive((await response.json()) as Live);
    } catch {
      return;
    }
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, 5000);
    return () => clearInterval(id);
  }, [load]);

  const stream = useEvents((e) => {
    if (e.kind === "run_started") {
      setLive((s) => ({ ...(s ?? { running: false, enabled: false }), running: true, run_id: e.data.run_id, started_at: e.data.at, step: "iniciando", agent: null, village: null }));
      router.refresh();
    }
    if (e.kind === "step") {
      setLive((s) => (s?.running ? { ...s, village: e.data.village ?? s.village, agent: e.data.agent, step: `${KIND_LABELS[e.data.kind] ?? e.data.kind}${e.data.tool ? ` ${e.data.tool}` : ""}` } : s));
    }
    if (e.kind === "run_finished") {
      load();
      router.refresh();
    }
  });

  const running = !!live?.running;
  const title = !live ? "Status indisponível" : running ? "Rodada em andamento" : live.enabled ? "Ocioso — agendamento ligado" : "Ocioso — agendamento desligado";
  const detail = !live
    ? "a API não respondeu"
    : running
      ? [live.village, live.agent ? agentLabel(live.agent) : null, live.step].filter(Boolean).join(" · ") + (live.started_at ? ` · começou ${relative(live.started_at)}` : "")
      : live.enabled && live.next_run_at
        ? `próxima rodada ${relative(live.next_run_at)}`
        : "rode manualmente ou ligue o agendamento nas configurações";

  return (
    <div role="status" aria-live="polite" className={cn("flex flex-col gap-3 rounded-lg border bg-surface p-4 sm:flex-row sm:items-center sm:p-5", running ? "border-foreground/40" : "border-border")}>
      <span className="relative flex size-10 shrink-0 items-center justify-center rounded-full border border-border bg-background">
        <Radio className={cn("size-4", running ? "text-status-ok" : "text-muted-foreground")} strokeWidth={1.75} />
        {running && <span aria-hidden className="live-dot absolute right-0 top-0 size-2.5 rounded-full bg-status-ok" />}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold">{title}</span>
          {running && live?.run_id && (
            <Link href={`/agents/${live.run_id}`} className="font-mono text-[12px] text-secondary underline-offset-4 hover:text-foreground hover:underline">{live.run_id}</Link>
          )}
        </div>
        <p className="mt-0.5 truncate text-[13px] text-secondary" suppressHydrationWarning>{detail}</p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Badge>{brain}</Badge>
        <Badge tone={stream === "live" ? "success" : stream === "retrying" ? "warning" : "neutral"}>{STREAM_LABEL[stream]}</Badge>
      </div>
    </div>
  );
}
