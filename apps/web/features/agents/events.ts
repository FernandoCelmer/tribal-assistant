"use client";

import { useEffect, useRef, useState } from "react";

export type RunEvent = {
  at: string;
  run_id: string;
  status: string;
  trigger: string;
  brain: string;
  model: string | null;
  dry_run: boolean;
  villages: number;
  actions_ok: number;
  actions_refused: number;
  actions_failed: number;
  tokens_in: number;
  tokens_out: number;
  error: string | null;
};

export type StepEvent = {
  at: string;
  run_id: string;
  seq: number;
  village: string | null;
  agent: string;
  kind: string;
  tool: string | null;
  content: string;
  is_error: boolean;
};

export type LogEvent = {
  at: string;
  level: string;
  source: string;
  message: string;
  process: string;
};

export type FlowNode = { key: string; source: string; action: string; title: string; priority: number; explored: boolean; reason?: string };

type FlowPlace = { village_id: number; village: string; coords: string; account_id?: number | null };

export type FlowEvent = FlowPlace &
  (
    | { phase: "start"; mode: string; role: string; specialists: { key: string; title: string }[] }
    | { phase: "plan"; proposals: FlowNode[] }
    | ({ phase: "running" } & FlowNode)
    | ({ phase: "result"; ok: boolean; text: string } & FlowNode)
    | ({ phase: "deferred"; why: string } & FlowNode)
    | { phase: "done"; summary: string; executed: number; failed: number; deferred: number; next_review_at: string | null }
  );

export type MicroEvent = { account_id?: number | null } & (
  | { step: "tool"; agent: string; tool: string; args: string; village_id: number }
  | { step: "result"; agent: string; tool: string; ok: boolean; text: string; village_id: number }
  | { step: "screen"; text: string }
  | { step: "click"; text: string }
  | { step: "request"; text: string; where: string; method: string }
  | { step: "motion"; text: string }
  | { step: "type"; text: string; field: string }
  | { step: "repair"; agent: string; tool: string; text: string; args: string; village_id: number }
);

export type StreamEvent =
  | { kind: "run_started"; data: RunEvent }
  | { kind: "run_finished"; data: RunEvent }
  | { kind: "step"; data: StepEvent }
  | { kind: "log"; data: LogEvent }
  | { kind: "sync"; data: { villages: number; reports: number; account_id?: number | null } }
  | { kind: "decision"; data: { action: string; ok: boolean; village_id: number; account_id?: number | null } }
  | { kind: "flow"; data: FlowEvent }
  | { kind: "micro"; data: MicroEvent };

export type StreamState = "connecting" | "live" | "retrying";

type Listener = { event: (e: StreamEvent) => void; state: (s: StreamState) => void };

const KINDS = ["run_started", "step", "run_finished", "log", "sync", "decision", "flow", "micro"] as const;

class Stream {
  private source: EventSource | null = null;
  private listeners = new Set<Listener>();
  private current: StreamState = "connecting";

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener.state(this.current);
    if (!this.source) this.open();
    return () => {
      this.listeners.delete(listener);
      if (this.listeners.size === 0) this.close();
    };
  }

  private open() {
    const source = new EventSource("/api/v1/events");
    this.source = source;
    this.set("connecting");
    source.onopen = () => this.set("live");
    source.onerror = () => this.set("retrying");
    for (const kind of KINDS) {
      source.addEventListener(kind, (e: MessageEvent<string>) => {
        let data: unknown;
        try {
          data = JSON.parse(e.data);
        } catch {
          return;
        }
        const event = { kind, data } as StreamEvent;
        for (const l of this.listeners) l.event(event);
      });
    }
  }

  private close() {
    this.source?.close();
    this.source = null;
    this.current = "connecting";
  }

  private set(state: StreamState) {
    this.current = state;
    for (const l of this.listeners) l.state(state);
  }
}

const stream = new Stream();

export function useEvents(handler: (event: StreamEvent) => void, enabled = true): StreamState {
  const latest = useRef(handler);
  latest.current = handler;
  const [state, setState] = useState<StreamState>("connecting");

  useEffect(() => {
    if (!enabled) return;
    return stream.subscribe({ event: (e) => latest.current(e), state: setState });
  }, [enabled]);

  return state;
}

export const STREAM_LABEL: Record<StreamState, string> = { connecting: "conectando…", live: "ao vivo", retrying: "reconectando…" };
