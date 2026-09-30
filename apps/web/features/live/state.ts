import type { FlowEvent, FlowNode, MicroEvent } from "@/features/agents/events";

export type Status = "pending" | "running" | "ok" | "failed" | "deferred";

export type Item = FlowNode & { status: Status; note: string; at: number };

export type Tick = { id: number; at: number; title: string; source: string; status: Status; note: string; village: string };

export type StepKind = MicroEvent["step"] | "log" | "trace" | "sync" | "run";

export type Step = { id: number; at: number; step: StepKind; agent: string; tool: string; text: string; args: string; ok: boolean | null };

export type Phase = "idle" | "thinking" | "deciding" | "acting" | "done";

export type LiveState = {
  village: string;
  coords: string;
  villageId: number | null;
  mode: string;
  specialists: { key: string; title: string }[];
  items: Item[];
  phase: Phase;
  active: string | null;
  summary: string;
  counts: { executed: number; failed: number; deferred: number };
  ticks: Tick[];
  steps: Step[];
  nextReview: number | null;
  updated: number;
};

export const SHOWN = 8;
const TICKS = 9;
const STEPS = 13;

export const EMPTY: LiveState = {
  village: "",
  coords: "",
  villageId: null,
  mode: "",
  specialists: [],
  items: [],
  phase: "idle",
  active: null,
  summary: "",
  counts: { executed: 0, failed: 0, deferred: 0 },
  ticks: [],
  steps: [],
  nextReview: null,
  updated: 0,
};

type Seed = {
  village: string;
  village_id: number;
  mode: string;
  created_at: string;
  next_review_at?: string | null;
  data: { executed?: SeedEntry[]; deferred?: SeedEntry[]; next_action?: string };
};

type SeedEntry = { key: string; source: string; action: string; title: string; priority: number; exploration?: boolean; ok?: boolean; result?: string; why?: string };

export function instant(text: string): number {
  const zoned = /[zZ]|[+-]\d\d:?\d\d$/.test(text) ? text : `${text}Z`;
  return Date.parse(zoned) || Date.now();
}

export function seed(specialists: { key: string; title: string }[], round: Seed | null): LiveState {
  if (!round) return { ...EMPTY, specialists };
  const at = instant(round.created_at);
  const entry = (e: SeedEntry, status: Status, note: string): Item => ({
    key: e.key,
    source: e.source,
    action: e.action,
    title: e.title,
    priority: e.priority,
    explored: !!e.exploration,
    status,
    note,
    at,
  });
  const executed = (round.data.executed ?? []).map((e) => entry(e, e.ok ? "ok" : "failed", e.result ?? ""));
  const deferred = (round.data.deferred ?? []).map((e) => entry(e, "deferred", e.why ?? ""));
  const items = [...executed, ...deferred.sort((a, b) => b.priority - a.priority)].slice(0, SHOWN);
  const failed = executed.filter((e) => e.status === "failed").length;
  return {
    ...EMPTY,
    specialists,
    village: round.village,
    villageId: round.village_id,
    mode: round.mode,
    items,
    phase: "done",
    counts: { executed: executed.length - failed, failed, deferred: deferred.length },
    nextReview: round.next_review_at ? instant(round.next_review_at) : null,
    ticks: executed.slice(0, TICKS).map((e, i) => ({ id: -i - 1, at, title: e.title, source: e.source, status: e.status, note: e.note, village: round.village })),
    updated: at,
  };
}

function place(items: Item[], node: FlowNode, patch: Partial<Item>): Item[] {
  const found = items.findIndex((i) => i.key === node.key);
  if (found >= 0) return items.map((i, n) => (n === found ? { ...i, ...patch } : i));
  const fresh: Item = { ...node, status: "pending", note: "", at: Date.now(), ...patch };
  if (items.length < SHOWN) return [...items, fresh];
  const drop = [...items].reverse().findIndex((i) => i.status === "pending" || i.status === "deferred");
  if (drop < 0) return [...items.slice(1), fresh];
  const index = items.length - 1 - drop;
  return [...items.slice(0, index), ...items.slice(index + 1), fresh];
}

let serial = 0;

export function reduce(state: LiveState, event: FlowEvent, only: number | null): LiveState {
  if (only !== null && event.village_id !== only) return state;
  const now = Date.now();
  const where = { village: event.village, coords: event.coords, villageId: event.village_id, updated: now };

  switch (event.phase) {
    case "start":
      return {
        ...state,
        ...where,
        mode: event.mode,
        specialists: event.specialists.length ? event.specialists : state.specialists,
        items: [],
        phase: "thinking",
        active: null,
        summary: "",
        counts: { executed: 0, failed: 0, deferred: 0 },
      };
    case "plan":
      return {
        ...state,
        ...where,
        items: event.proposals.slice(0, SHOWN).map((p) => ({ ...p, status: "pending", note: "", at: now })),
        phase: "deciding",
      };
    case "running":
      return { ...state, ...where, items: place(state.items, event, { status: "running", at: now }), phase: "acting", active: event.key };
    case "result": {
      const status: Status = event.ok ? "ok" : "failed";
      const tick: Tick = { id: ++serial, at: now, title: event.title, source: event.source, status, note: event.text, village: event.village };
      return {
        ...state,
        ...where,
        items: place(state.items, event, { status, note: event.text, at: now }),
        active: null,
        ticks: [tick, ...state.ticks].slice(0, TICKS),
      };
    }
    case "deferred": {
      if (!state.items.some((i) => i.key === event.key)) return { ...state, updated: now };
      return { ...state, ...where, items: place(state.items, event, { status: "deferred", note: event.why }) };
    }
    case "done":
      return {
        ...state,
        ...where,
        phase: "done",
        active: null,
        summary: event.summary,
        nextReview: event.next_review_at ? instant(event.next_review_at) : null,
        counts: { executed: event.executed, failed: event.failed, deferred: event.deferred },
      };
  }
}

export function micro(state: LiveState, event: MicroEvent, only: number | null): LiveState {
  if (only !== null && "village_id" in event && event.village_id !== only) return state;
  const base = { id: ++serial, at: Date.now(), step: event.step, agent: "", tool: "", text: "", args: "", ok: null };
  const step: Step =
    event.step === "tool"
      ? { ...base, agent: event.agent, tool: event.tool, args: event.args }
      : event.step === "result"
        ? { ...base, agent: event.agent, tool: event.tool, text: event.text, ok: event.ok }
        : event.step === "request"
          ? { ...base, text: event.text, args: event.where }
          : event.step === "type"
            ? { ...base, text: event.text, args: event.field }
          : { ...base, text: event.text };
  const last = state.steps[0];
  if (last && last.step === step.step && last.text === step.text && last.tool === step.tool && step.step !== "tool") return state;
  return { ...state, steps: [step, ...state.steps].slice(0, STEPS) };
}

export function note(state: LiveState, step: StepKind, text: string, ok: boolean | null = null, agent = ""): LiveState {
  if (!text) return state;
  const entry: Step = { id: ++serial, at: Date.now(), step, agent, tool: "", text, args: "", ok };
  const last = state.steps[0];
  if (last && last.step === step && last.text === text) return state;
  return { ...state, steps: [entry, ...state.steps].slice(0, STEPS) };
}

export function history(state: LiveState, logs: { at: string; level: string; message: string }[]): LiveState {
  if (state.steps.length) return state;
  const steps: Step[] = logs.map((log) => ({
    id: ++serial,
    at: instant(log.at),
    step: "log",
    agent: "",
    tool: "",
    text: log.message,
    args: "",
    ok: log.level === "ERROR" || log.level === "WARNING" ? false : null,
  }));
  return { ...state, steps: steps.slice(0, STEPS) };
}
