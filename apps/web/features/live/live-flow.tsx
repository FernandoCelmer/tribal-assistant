"use client";

import { useEffect, useMemo, useReducer, useState } from "react";
import { STREAM_LABEL, useEvents, type FlowEvent, type MicroEvent, type StreamState } from "@/features/agents/events";
import { agentLabel, readable, toolLabel } from "@/features/flow/labels";
import { ROLES } from "@/lib/game";
import { SIDE_CSS, VillagePanel } from "./village-panel";
import { EMPTY, SHOWN, history, micro, note, reduce, seed, type Item, type LiveState, type Phase, type Status, type Step, type StepKind } from "./state";

const W = 1280;
const H = 720;
const MAIN = 940;
const SPEC_X = 170;
const HUB = { x: 450, y: 290 };
const ACT_X = 590;
const TOP = 134;
const BOTTOM = 452;
const SPEC_TOP = 122;
const SPEC_BOTTOM = 456;

const TONE: Record<Status, string> = {
  pending: "var(--live-pending)",
  running: "var(--live-running)",
  ok: "var(--live-ok)",
  failed: "var(--live-bad)",
  deferred: "var(--live-muted)",
};

const MARK: Record<Status, string> = { pending: "·", running: "…", ok: "✓", failed: "✕", deferred: "‖" };

const PHASE: Record<Phase, string> = {
  idle: "aguardando rodada",
  thinking: "especialistas analisando",
  deciding: "coordenador priorizando",
  acting: "executando",
  done: "rodada concluída",
};

const QUIET_LOG = /uvicorn|apscheduler|event_relay/;
const TRACE_KINDS = new Set(["plan", "summary", "thought", "info", "error"]);

const GLYPH: Record<StepKind, string> = { tool: "⚙", result: "", screen: "↳", click: "↳", log: "›", trace: "◆", sync: "⟳", run: "●" };
const NOTE_LABEL: Partial<Record<StepKind, string>> = { log: "log", trace: "plano", sync: "sync", run: "rodada" };

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

function spread(count: number, index: number, top = TOP, bottom = BOTTOM): number {
  if (count <= 1) return (top + bottom) / 2;
  return top + ((bottom - top) * index) / (count - 1);
}

function curve(x1: number, y1: number, x2: number, y2: number): string {
  const mid = (x1 + x2) / 2;
  return `M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`;
}

function clip(text: string, size: number): string {
  return text.length > size ? `${text.slice(0, size - 1)}…` : text;
}

function label(item: Pick<Item, "title">): string {
  return readable(item.title);
}

function useStage(): number {
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const fit = () => setScale(Math.min(window.innerWidth / W, window.innerHeight / H));
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);
  return scale;
}

function useClock(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1_000);
    return () => clearInterval(timer);
  }, []);
  return now;
}

function ago(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.round(s / 60);
  return m < 60 ? `${m}min` : `${Math.round(m / 60)}h`;
}

export function LiveFlow({ only, transparent }: { only: number | null; transparent: boolean }) {
  const [state, dispatch] = useReducer(reducer, EMPTY);
  const scale = useStage();
  const now = useClock();

  const stream: StreamState = useEvents((event) => {
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

  const specs = state.specialists;
  const specY = useMemo(() => new Map(specs.map((s, i) => [s.key, spread(specs.length, i, SPEC_TOP, SPEC_BOTTOM)])), [specs]);
  const items = state.items;
  const itemY = (i: number) => spread(Math.max(items.length, 1), i, items.length < 4 ? 200 : TOP, items.length < 4 ? 380 : BOTTOM);
  const sources = new Map<string, Status>();
  for (const item of items) {
    const current = sources.get(item.source);
    if (item.status === "running" || !current || current === "pending" || current === "deferred") sources.set(item.source, item.status);
  }
  const thinking = state.phase === "thinking";
  const busy = state.phase !== "done" && state.phase !== "idle";
  const running = items.find((i) => i.status === "running");
  const quiet = state.updated ? now - state.updated : 0;

  return (
    <div className="live-root" data-transparent={transparent || undefined}>
      <style>{CSS + SIDE_CSS}</style>
      <div className="live-stage" style={{ width: W, height: H, transform: `scale(${scale})` }}>
        <header className="live-head">
          <span className="live-dot" data-state={stream} />
          <span className="live-tag">{stream === "live" ? "AO VIVO" : STREAM_LABEL[stream].toUpperCase()}</span>
          <span className="live-title">
            {state.village ? clip(state.village, 26) : "Tribal Assistant"}
            {state.coords && <span className="live-dim"> {state.coords}</span>}
          </span>
          {state.mode && <span className="live-mode">modo {(ROLES[state.mode] ?? state.mode).toLowerCase()}</span>}
          <span className="live-phase" data-phase={state.phase}>
            {PHASE[state.phase]}
            {state.phase === "done" && quiet > 0 && <span className="live-dim"> · há {ago(quiet)}</span>}
          </span>
        </header>

        <div className="live-panel live-graph-panel">
          <div className="live-cap">Fluxo de decisões</div>
        </div>

        <svg className="live-graph" viewBox={`0 0 ${MAIN} ${H}`} width={MAIN} height={H} aria-label="fluxo de decisões dos agentes">
          <defs>
            <radialGradient id="hub-glow">
              <stop offset="0%" stopColor="var(--live-running)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="var(--live-running)" stopOpacity="0" />
            </radialGradient>
          </defs>

          {specs.map((s, index) => {
            const y = specY.get(s.key) ?? 0;
            const status = sources.get(s.key);
            const path = curve(SPEC_X + 8, y, HUB.x - 40, HUB.y);
            const on = !!status || thinking;
            const fast = thinking || status === "running";
            return (
              <g key={`e-${s.key}`}>
                <path d={path} className="live-edge" data-on={on || undefined} data-flow={on || undefined} style={{ stroke: status ? TONE[status] : undefined }} />
                <circle r={status === "running" ? 4 : fast ? 2.8 : 1.8} className="live-spark" data-idle={!fast || undefined} style={{ fill: status ? TONE[status] : "var(--live-pending)" }}>
                  <animateMotion dur={status === "running" ? "0.9s" : fast ? `${1.4 + (index % 5) / 5}s` : `${3.5 + (index % 7) * 0.6}s`} begin={`${(index * 0.37) % 3}s`} repeatCount="indefinite" path={path} />
                </circle>
              </g>
            );
          })}

          {items.map((item, i) => {
            const y = itemY(i);
            const path = curve(HUB.x + 40, HUB.y, ACT_X - 9, y);
            const live = item.status === "running" || item.status === "pending";
            return (
              <g key={`a-${item.key}`}>
                <path d={path} className="live-edge" data-on data-flow={live || undefined} style={{ stroke: TONE[item.status] }} data-dash={item.status === "deferred" || undefined} />
                <circle r={item.status === "running" ? 4.5 : 2} className="live-spark" data-idle={item.status !== "running" || undefined} style={{ fill: TONE[item.status] }}>
                  <animateMotion dur={item.status === "running" ? "0.8s" : `${3 + (i % 4) * 0.7}s`} begin={`${(i * 0.53) % 2}s`} repeatCount="indefinite" path={path} />
                </circle>
              </g>
            );
          })}

          {specs.map((s) => {
            const y = specY.get(s.key) ?? 0;
            const status = sources.get(s.key);
            return (
              <g key={`s-${s.key}`} className="live-spec" data-on={!!status || undefined} data-think={thinking || undefined}>
                <circle cx={SPEC_X} cy={y} r={status === "running" ? 8 : 6} style={{ fill: status ? TONE[status] : undefined }} />
                <text x={SPEC_X - 14} y={y + 4} textAnchor="end">
                  {agentLabel(s.key) || s.title}
                </text>
              </g>
            );
          })}

          <circle cx={HUB.x} cy={HUB.y} r={70} fill="url(#hub-glow)" className="live-hub-glow" data-on={busy || undefined} />
          <circle cx={HUB.x} cy={HUB.y} r={48} className="live-orbit" data-busy={busy || undefined} />
          <g className="live-hub" data-phase={state.phase}>
            <circle cx={HUB.x} cy={HUB.y} r={40} />
            <text x={HUB.x} y={HUB.y - 2} textAnchor="middle" className="live-hub-name">
              Coordenador
            </text>
            <text x={HUB.x} y={HUB.y + 13} textAnchor="middle" className="live-hub-sub">
              {items.length ? `${items.length}${items.length >= SHOWN ? "+" : ""} propostas` : "—"}
            </text>
          </g>

          {items.map((item, i) => {
            const y = itemY(i);
            return (
              <g key={`n-${item.key}-${item.status}`} className="live-act" data-status={item.status}>
                {(item.status === "ok" || item.status === "failed") && <circle cx={ACT_X} cy={y} r={8} className="live-ring" style={{ stroke: TONE[item.status] }} />}
                <circle cx={ACT_X} cy={y} r={8} style={{ fill: TONE[item.status] }} />
                <text x={ACT_X} y={y + 3.5} textAnchor="middle" className="live-mark">
                  {MARK[item.status]}
                </text>
                <text x={ACT_X + 18} y={y - 2} className="live-act-title">
                  {clip(label(item), 36)}
                  {item.explored && <tspan className="live-explore"> ✦ explorando</tspan>}
                </text>
                <text x={ACT_X + 18} y={y + 13} className="live-act-note">
                  {clip(`${agentLabel(item.source)} · ${item.priority.toFixed(0)} pts${item.note ? ` · ${readable(item.note)}` : ""}`, 56)}
                </text>
              </g>
            );
          })}

          {!items.length && (
            <text x={ACT_X + 18} y={HUB.y + 4} className="live-act-note">
              {thinking ? "reunindo propostas…" : "sem decisões ainda"}
            </text>
          )}
        </svg>

        <section className="live-bottom">
          <div className="live-steps">
            <div className="live-cap">
              Passo a passo
              {running && <span className="live-now"> · agora: {clip(label(running), 48)}</span>}
            </div>
            <ol>
              {state.steps.map((s) => (
                <StepLine key={s.id} step={s} age={now - s.at} />
              ))}
              {!state.steps.length && <li className="live-dim">esperando o próximo passo…</li>}
            </ol>
          </div>
          <div className="live-results">
            <div className="live-cap">
              Resultados
              {state.phase === "done" && state.updated > 0 && (
                <span className="live-dim">
                  {" "}
                  · {state.counts.executed} feita(s)
                  {state.counts.failed > 0 && <span className="live-bad"> · {state.counts.failed} falha(s)</span>} · {state.counts.deferred} adiada(s)
                </span>
              )}
            </div>
            <ul className="live-ticks">
              {state.ticks.map((t) => (
                <li key={t.id} data-status={t.status}>
                  <span className="live-tick-mark">{MARK[t.status]}</span>
                  <span className="live-tick-text">{clip(label(t), 32)}</span>
                  <span className="live-tick-age">{ago(now - t.at)}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <VillagePanel only={only} now={now} nextReview={state.nextReview} />
      </div>
    </div>
  );
}

function StepLine({ step, age }: { step: Step; age: number }) {
  const fresh = age < 2_500;
  if (step.step === "tool") {
    return (
      <li data-step="tool" data-fresh={fresh || undefined}>
        <span className="live-glyph">{GLYPH.tool}</span>
        <b>{agentLabel(step.agent)}</b> <span className="live-dim">→</span> {toolLabel(step.tool)}
        {step.args && <code className="live-args">{clip(readable(step.args), 70)}</code>}
      </li>
    );
  }
  if (step.step === "result") {
    return (
      <li data-step="result" data-ok={step.ok ? "" : undefined} data-fresh={fresh || undefined}>
        <span className="live-glyph">{step.ok ? "✓" : "✕"}</span>
        <span className="live-dim">{toolLabel(step.tool)}:</span> {clip(readable(step.text), 80)}
      </li>
    );
  }
  if (step.step !== "screen" && step.step !== "click") {
    return (
      <li data-step={step.step} data-bad={step.ok === false ? "" : undefined} data-fresh={fresh || undefined}>
        <span className="live-glyph">{GLYPH[step.step]}</span>
        <span className="live-kind">{step.agent ? agentLabel(step.agent) : NOTE_LABEL[step.step]}</span> {clip(readable(step.text), 96)}
      </li>
    );
  }
  return (
    <li data-step={step.step} data-fresh={fresh || undefined}>
      <span className="live-glyph">{GLYPH[step.step]}</span>
      {step.step === "screen" ? "abrindo tela " : "clicando "}
      <b>{step.step === "click" ? `“${clip(step.text, 40)}”` : step.text}</b>
    </li>
  );
}

const CSS = `
.live-root {
  --live-bg: var(--background);
  --live-panel: var(--surface);
  --live-line: var(--border);
  --live-text: var(--text-primary);
  --live-dim: var(--text-secondary);
  --live-pending: var(--text-muted);
  --live-running: var(--status-warn);
  --live-ok: var(--status-ok);
  --live-bad: var(--status-bad);
  --live-muted: var(--text-disabled);
  --live-explore: #c4b5fd;
  position: fixed; inset: 0; overflow: hidden; background: var(--live-bg);
  font-family: var(--font-sans, system-ui, sans-serif); color: var(--live-text);
  display: flex; align-items: center; justify-content: center;
}
.live-root[data-transparent] { background: transparent; }
.live-stage { position: relative; flex: none; transform-origin: center; background: var(--live-bg); }
.live-root[data-transparent] .live-stage { background: transparent; }
.live-panel, .live-head, .live-steps, .live-results, .live-side { background: var(--live-panel); border: 1px solid var(--live-line); border-radius: 8px; overflow: hidden; }
.live-graph-panel { position: absolute; top: 72px; left: 12px; width: 916px; height: 400px; }
.live-head { position: absolute; top: 12px; left: 12px; right: 12px; height: 48px; display: flex; align-items: center; gap: 12px; padding: 0 16px; font-size: 14px; z-index: 1; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--live-ok); animation: live-pulse 1.6s ease-in-out infinite; }
.live-dot[data-state="connecting"], .live-dot[data-state="retrying"] { background: var(--live-running); }
.live-tag { display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 2px 8px; font-size: 12px; font-weight: 500; border: 1px solid color-mix(in srgb, var(--live-ok) 30%, transparent); background: color-mix(in srgb, var(--live-ok) 10%, transparent); color: var(--live-ok); }
.live-title { font-weight: 600; font-size: 15px; }
.live-mode { font-size: 12px; font-weight: 500; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--live-line); color: var(--live-dim); }
.live-phase { margin-left: auto; font-size: 13px; color: var(--live-dim); }
.live-phase[data-phase="acting"], .live-phase[data-phase="deciding"], .live-phase[data-phase="thinking"] { color: var(--live-running); }
.live-dim { color: var(--live-dim); font-weight: 400; }
.live-bad { color: var(--live-bad); }
.live-graph { position: absolute; top: 0; left: 0; pointer-events: none; }
.live-edge { fill: none; stroke: var(--live-line); stroke-width: 1.5; opacity: .55; transition: stroke .4s, opacity .4s; }
.live-edge[data-on] { opacity: .9; stroke-width: 2; }
.live-edge[data-flow] { stroke-dasharray: 6 6; animation: live-flow 1.2s linear infinite; }
.live-edge[data-dash] { stroke-dasharray: 4 5; opacity: .55; animation: none; }
.live-spark { filter: drop-shadow(0 0 4px currentColor); }
.live-spark[data-idle] { opacity: .45; filter: none; }
.live-spec circle { fill: var(--live-muted); stroke: var(--live-panel); stroke-width: 2; transition: r .3s, fill .3s; }
.live-spec[data-think] circle { animation: live-think 1.4s ease-in-out infinite; }
.live-spec text { font-size: 12.5px; fill: var(--live-dim); transition: fill .3s; }
.live-spec[data-on] text { fill: var(--live-text); font-weight: 600; }
.live-orbit { fill: none; stroke: var(--live-pending); stroke-width: 1.2; stroke-dasharray: 3 9; opacity: .5; transform-box: fill-box; transform-origin: center; animation: live-spin 14s linear infinite; }
.live-orbit[data-busy] { stroke: var(--live-running); opacity: .9; animation-duration: 3s; }
.live-hub circle { fill: var(--live-bg); stroke: var(--live-pending); stroke-width: 2; }
.live-hub[data-phase="deciding"] circle, .live-hub[data-phase="acting"] circle { stroke: var(--live-running); }
.live-hub-name { font-size: 11px; font-weight: 700; fill: var(--live-text); }
.live-hub-sub { font-size: 10px; fill: var(--live-dim); }
.live-hub-glow { opacity: 0; transition: opacity .5s; }
.live-hub-glow[data-on] { opacity: 1; animation: live-glow 2s ease-in-out infinite; }
.live-act circle { stroke: var(--live-panel); stroke-width: 2; }
.live-act[data-status="running"] > circle:not(.live-ring) { animation: live-think .8s ease-in-out infinite; }
.live-ring { fill: none; stroke-width: 2; animation: live-ring 1.2s ease-out forwards; }
.live-mark { font-size: 10px; font-weight: 800; fill: var(--live-bg); pointer-events: none; }
.live-act-title { font-size: 14px; font-weight: 600; fill: var(--live-text); }
.live-act[data-status="deferred"] .live-act-title { fill: var(--live-dim); font-weight: 500; }
.live-act-note { font-size: 11px; fill: var(--live-dim); }
.live-explore { fill: var(--live-explore); font-size: 11px; font-weight: 600; }
.live-bottom { position: absolute; left: 12px; width: 916px; top: 484px; height: 224px; display: grid; grid-template-columns: 1fr 300px; gap: 12px; }
.live-cap { display: flex; align-items: center; gap: 6px; min-height: 40px; padding: 0 14px; border-bottom: 1px solid var(--live-line); font-size: 13px; font-weight: 600; color: var(--live-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.live-now { color: var(--live-running); font-weight: 500; font-size: 12px; overflow: hidden; text-overflow: ellipsis; }
.live-steps { overflow: hidden; }
.live-steps ol { padding: 8px 14px !important; }
.live-ticks { padding: 8px 14px !important; }
.live-steps ol { margin: 0; padding: 0; list-style: none; font-size: 12px; line-height: 16.5px; }
.live-steps li { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--live-dim); animation: live-in .35s ease-out; }
.live-steps li[data-fresh] { color: var(--live-text); }
.live-steps li:nth-child(n+8) { opacity: .5; }
.live-steps li[data-step="tool"] b { color: var(--live-text); }
.live-steps li[data-step="result"] .live-glyph { color: var(--live-bad); }
.live-steps li[data-step="result"][data-ok] .live-glyph { color: var(--live-ok); }
.live-steps li[data-bad] .live-glyph, .live-steps li[data-bad] .live-kind { color: var(--live-bad); }
.live-steps li[data-step="sync"] .live-glyph, .live-steps li[data-step="run"] .live-glyph { color: var(--live-ok); }
.live-kind { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: var(--live-pending); margin-right: 2px; }
.live-glyph { display: inline-block; width: 16px; color: var(--live-running); font-weight: 700; }
.live-args { margin-left: 8px; font-family: var(--font-mono, ui-monospace, monospace); font-size: 11px; color: var(--live-dim); background: var(--surface-hover); padding: 1px 6px; border-radius: 4px; }
.live-results { overflow: hidden; }
.live-ticks { margin: 0; padding: 0; list-style: none; font-size: 12px; line-height: 22px; }
.live-ticks li { display: flex; gap: 6px; white-space: nowrap; animation: live-in .5s ease-out; }
.live-tick-text { overflow: hidden; text-overflow: ellipsis; }
.live-tick-age { margin-left: auto; color: var(--live-dim); }
.live-tick-mark { flex: none; display: inline-block; width: 12px; font-weight: 800; }
.live-ticks li[data-status="ok"] .live-tick-mark { color: var(--live-ok); }
.live-ticks li[data-status="failed"] .live-tick-mark { color: var(--live-bad); }
@keyframes live-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
@keyframes live-think { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
@keyframes live-glow { 0%, 100% { opacity: .6; } 50% { opacity: 1; } }
@keyframes live-ring { from { r: 8; opacity: 1; } to { r: 22; opacity: 0; } }
@keyframes live-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes live-flow { to { stroke-dashoffset: -24; } }
@keyframes live-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .live-root *, .live-root *::before { animation: none !important; } }
`;
