"use client";

import { Eye, Pickaxe, Swords, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { agentLabel, readable, toolLabel } from "@/features/flow/labels";
import type { Step } from "@/features/live/state";
import { clip, useClock, useLiveFeed } from "@/features/live/use-live";
import { RESOURCES, ROLES } from "@/lib/game";
import { countdown, instant, number, useOverview, type Command, type Overview, type Village } from "./data";
import { FlowGraph, chosen } from "./graph";
import { Highlights } from "./highlights";
import { TWITCH_CSS } from "./styles";

const SITE = "tw.fernandocelmer.com/live";
const ACTIVITY = 14;
const STATE_LABEL = { running: "Em execução", ok: "Feita", failed: "Falhou", deferred: "Adiada", pending: "Na fila" } as const;

function useSince(fromUrl: string | null): number {
  const [since, setSince] = useState(() => Date.now());
  useEffect(() => {
    const parsed = fromUrl ? Date.parse(fromUrl) : NaN;
    if (Number.isFinite(parsed)) setSince(parsed);
  }, [fromUrl]);
  return since;
}

function time(at: number): string {
  return new Date(at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function describe(step: Step): string {
  switch (step.step) {
    case "tool":
      return `${agentLabel(step.agent)}: ${toolLabel(step.tool)}${step.args ? ` (${readable(step.args)})` : ""}`;
    case "result":
      return `${step.ok ? "✓" : "✕"} ${toolLabel(step.tool)}: ${readable(step.text)}`;
    case "screen":
      return `Na tela ${step.text}`;
    case "click":
      return step.text && step.text !== "elemento" ? `Clicando em “${step.text}”` : "Clicando";
    case "type":
      return `Digitando “${step.text}”${step.args ? ` em ${step.args}` : ""}`;
    case "request":
      return `Enviando ao jogo: ${step.text}${step.args ? ` em ${step.args}` : ""}`;
    case "repair":
      return `Erro lido (${step.text}); nova tentativa com ${step.args}`;
    default:
      return readable(step.text);
  }
}

function Header({ village, mode, next, now, incoming }: { village: Village | undefined; mode: string; next: number | null; now: number; incoming: Command[] }) {
  return (
    <header className="tw-header">
      <div className="tw-header-left">
        <span className="tw-live-dot" />
        <span className="tw-live">AO VIVO</span>
        <strong className="tw-village">{village?.name ?? "Tribal Assistant"}</strong>
        {village && <span className="tw-secondary">{village.coords}</span>}
        {mode && <span className="tw-chip">modo {(ROLES[mode] ?? mode).toLowerCase()}</span>}
      </div>
      <div className="tw-header-center">
        {incoming.length ? (
          <span className="tw-alert">
            ⚠ {incoming.length} ataque{incoming.length > 1 ? "s" : ""} chegando · {countdown(instant(incoming[0].arrival_at), now)}
          </span>
        ) : (
          SITE
        )}
      </div>
      <div className="tw-header-right">
        <span className="tw-secondary">próxima rodada</span>
        <b className="tw-count">{next ? (next > now ? countdown(next, now) : "agora") : "—"}</b>
      </div>
    </header>
  );
}

function VillageCard({ village, overview }: { village: Village; overview: Overview }) {
  const player = overview.player;
  const protection = instant(player?.protection_until);
  const now = Date.now();
  const since = village.synced_at ? (now - instant(village.synced_at)) / 3_600_000 : 0;
  const stock = (r: "wood" | "clay" | "iron") => Math.min(village.storage, village[r] + village[`${r}_prod`] * Math.max(0, since));
  const [x, y] = village.coords.split("|").map(Number);
  const continent = `K${Math.floor(y / 100)}${Math.floor(x / 100)}`;
  return (
    <section className="tw-panel tw-village-card">
      <header className="tw-head">
        <h2>Aldeia — {village.name}</h2>
        <span className="tw-secondary">
          ({village.coords}) {continent}
        </span>
      </header>
      <div className="tw-body">
        <div className="tw-score">
          <div>
            <strong>{number(player?.points ?? village.points)}</strong> <span className="tw-secondary">pts</span>
            {player?.rank ? <span className="tw-secondary tw-rank">#{number(player.rank)}</span> : null}
          </div>
          {protection > now && <span className="tw-protect">proteção {countdown(protection, now)}</span>}
        </div>
        <div className="tw-resources">
          {(["wood", "iron", "clay"] as const).map((r) => (
            <div key={r} className="tw-resource">
              <img src={RESOURCES[r].icon} alt={RESOURCES[r].label} width={20} height={20} />
              <b>{number(stock(r))}</b>
            </div>
          ))}
          <div className="tw-resource">
            <Users size={18} className="tw-pop-icon" />
            <b>
              {number(village.pop_current)} <span className="tw-secondary">/ {number(village.pop_max)}</span>
            </b>
          </div>
        </div>
      </div>
    </section>
  );
}

function DecisionCard({ items }: { items: ReturnType<typeof useLiveFeed>["state"]["items"] }) {
  const pick = chosen(items);
  return (
    <section className="tw-panel">
      <header className="tw-head">
        <h2>Decisão atual</h2>
      </header>
      <div className="tw-body tw-decision">
        {pick ? (
          <>
            <div>
              <span className="tw-secondary">{agentLabel(pick.source)}</span>
              <strong>{clip(readable(pick.title), 44)}</strong>
              <span className="tw-secondary">{clip(readable(pick.note || pick.reason || ""), 70) || "—"}</span>
            </div>
            <span className="tw-state" data-status={pick.status}>
              {pick.status === "deferred" && /falta|dispon/i.test(pick.note) ? "Aguardando" : STATE_LABEL[pick.status]}
            </span>
          </>
        ) : (
          <span className="tw-secondary">nenhuma decisão nesta rodada ainda</span>
        )}
      </div>
    </section>
  );
}

export function MovesList({ overview, village, now }: { overview: Overview; village: Village; now: number }) {
  const commands = overview.commands.filter((c) => instant(c.arrival_at) > now).sort((a, b) => instant(a.arrival_at) - instant(b.arrival_at));
  const scavenging = village.scavenge.filter((s) => s.return_at && instant(s.return_at) > now);
  return (
      <ul className="tw-body tw-list">
        {commands.map((c, i) => {
          const Icon = /explor|espi/i.test(c.label) ? Eye : Swords;
          return (
            <li key={i} data-incoming={c.direction === "in" || undefined}>
              <Icon size={16} />
              <span className="tw-truncate">
                {c.label || c.kind} {c.coords && !(c.label || "").includes(c.coords) && <span className="tw-secondary">({c.coords})</span>}
              </span>
              <b className="tw-count">{countdown(instant(c.arrival_at), now)}</b>
            </li>
          );
        })}
        {scavenging.map((s) => (
          <li key={s.option_id}>
            <Pickaxe size={16} />
            <span className="tw-truncate">{s.name}</span>
            <b className="tw-count">{countdown(instant(s.return_at), now)}</b>
          </li>
        ))}
        {!commands.length && !scavenging.length && <li className="tw-secondary">nada em trânsito</li>}
      </ul>
  );
}

function MovesCard(props: { overview: Overview; village: Village; now: number }) {
  return (
    <section className="tw-panel tw-moves">
      <header className="tw-head">
        <h2>Movimentos</h2>
      </header>
      <MovesList {...props} />
    </section>
  );
}

function useCompact(): boolean {
  const [compact, setCompact] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(max-height: 900px)");
    const update = () => setCompact(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return compact;
}

function Activity({ steps }: { steps: Step[] }) {
  return (
    <section className="tw-panel tw-activity">
      <header className="tw-head">
        <h2>Atividade ao vivo</h2>
      </header>
      <ol className="tw-body tw-events">
        {steps.slice(0, ACTIVITY).map((step) => (
          <li key={step.id} data-bad={step.ok === false || undefined}>
            <time>{time(step.at)}</time>
            <span>{clip(describe(step), 140)}</span>
          </li>
        ))}
        {!steps.length && <li className="tw-secondary">esperando o próximo passo…</li>}
      </ol>
    </section>
  );
}

export function TwitchScreen({ only, since: sinceParam, transparent }: { only: number | null; since: string | null; transparent: boolean }) {
  const { state } = useLiveFeed(only);
  const overview = useOverview();
  const now = useClock();
  const since = useSince(sinceParam);
  const compact = useCompact();
  const village = overview?.villages.find((v) => only === null || v.id === only) ?? overview?.villages[0];
  const incoming = (overview?.commands ?? []).filter((c) => c.direction === "in" && instant(c.arrival_at) > now);

  return (
    <div className="tw-root" data-transparent={transparent || undefined}>
      <style>{TWITCH_CSS}</style>
      <Header village={village} mode={state.mode} next={state.nextReview} now={now} incoming={incoming} />

      <main className="tw-top">
        <section className="tw-game" aria-label="janela do jogo (captura do OBS)" />
        <aside className="tw-side">
          {village && overview ? <VillageCard village={village} overview={overview} /> : <section className="tw-panel tw-village-card" />}
          <DecisionCard items={state.items} />
          {!compact && (village && overview ? <MovesCard overview={overview} village={village} now={now} /> : <section className="tw-panel tw-moves" />)}
          {village && overview ? (
            <Highlights overview={overview} village={village} items={state.items} steps={state.steps} since={since} now={now} moves={compact ? <MovesList overview={overview} village={village} now={now} /> : null} />
          ) : (
            <section className="tw-panel tw-highlights" />
          )}
        </aside>
      </main>

      <section className="tw-bottom">
        <section className="tw-panel tw-flow">
          <header className="tw-head">
            <h2>Fluxo de decisões dos agentes</h2>
          </header>
          <FlowGraph specialists={state.specialists} items={state.items} thinking={state.phase === "thinking"} />
        </section>
        <Activity steps={state.steps} />
      </section>
    </div>
  );
}
