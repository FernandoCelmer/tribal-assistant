"use client";

import { useEffect, useReducer, useState } from "react";
import { useEvents, type FlowEvent, type MicroEvent, type StreamState } from "@/features/agents/events";
import { EMPTY, history, micro, note, reduce, seed, type LiveState, type StepKind } from "./state";

export const QUIET_LOG = /uvicorn|apscheduler|event_relay/;
const TRACE_KINDS = new Set(["plan", "summary", "thought", "info", "error"]);

type Action =
  | { type: "seed"; state: LiveState }
  | { type: "history"; logs: { at: string; level: string; message: string }[] }
  | { type: "flow"; event: FlowEvent; only: number | null }
  | { type: "micro"; event: MicroEvent; only: number | null }
  | { type: "note"; step: StepKind; text: string; ok?: boolean | null; agent?: string };

function reducer(state: LiveState, action: Action): LiveState {
  if (action.type === "seed") return state.updated > action.state.updated ? state : { ...action.state, steps: state.steps };
  if (action.type === "history") return history(state, action.logs);
  if (action.type === "micro") return micro(state, action.event, action.only);
  if (action.type === "note") return note(state, action.step, action.text, action.ok ?? null, action.agent ?? "");
  return reduce(state, action.event, action.only);
}

export function useLiveFeed(only: number | null): { state: LiveState; stream: StreamState } {
  const [state, dispatch] = useReducer(reducer, EMPTY);

  const stream = useEvents((event) => {
    if (event.kind === "flow") dispatch({ type: "flow", event: event.data, only });
    if (event.kind === "micro") dispatch({ type: "micro", event: event.data, only });
    if (event.kind === "log" && !QUIET_LOG.test(event.data.source) && event.data.level !== "DEBUG")
      dispatch({ type: "note", step: "log", text: event.data.message, ok: event.data.level === "ERROR" || event.data.level === "WARNING" ? false : null });
    if (event.kind === "step" && TRACE_KINDS.has(event.data.kind))
      dispatch({ type: "note", step: "trace", text: event.data.content, agent: event.data.agent, ok: event.data.is_error ? false : null });
    if (event.kind === "sync") dispatch({ type: "note", step: "sync", text: `sincronizou ${event.data.villages} aldeia(s) e ${event.data.reports} relatório(s)` });
    if (event.kind === "run_started") dispatch({ type: "note", step: "run", text: `rodada ${event.data.run_id} começou (${event.data.trigger})` });
    if (event.kind === "run_finished")
      dispatch({ type: "note", step: "run", text: `rodada terminou: ${event.data.actions_ok} feita(s), ${event.data.actions_failed} falha(s)`, ok: event.data.status !== "failed" });
  });

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const [specialists, rounds, logs] = await Promise.all([
          fetch("/api/v1/agents/proposers").then((r) => (r.ok ? r.json() : [])),
          fetch("/api/v1/agents/coordination").then((r) => (r.ok ? r.json() : [])),
          fetch("/api/v1/logs?limit=30&level=INFO").then((r) => (r.ok ? r.json() : [])),
        ]);
        const recent = (logs as { at: string; level: string; message: string; source: string }[]).filter((l) => !QUIET_LOG.test(l.source) && l.level !== "DEBUG");
        if (alive) dispatch({ type: "history", logs: recent });
        const pool = (rounds as { village_id: number; created_at: string }[]).filter((r) => only === null || r.village_id === only);
        const latest = pool.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))[0] ?? null;
        const list = (specialists as { key: string; title: string }[]).map(({ key, title }) => ({ key, title }));
        if (alive) dispatch({ type: "seed", state: seed(list, latest as Parameters<typeof seed>[1]) });
      } catch {
        return;
      }
    };
    load();
    return () => {
      alive = false;
    };
  }, [only]);

  return { state, stream };
}

export function useClock(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1_000);
    return () => clearInterval(timer);
  }, []);
  return now;
}

export function ago(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.round(s / 60);
  return m < 60 ? `${m}min` : `${Math.round(m / 60)}h`;
}

export function clip(text: string, size: number): string {
  return text.length > size ? `${text.slice(0, size - 1)}…` : text;
}
