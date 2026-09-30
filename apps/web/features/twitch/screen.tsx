"use client";

import { Eye, Pickaxe, Swords, Users } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { agentLabel, readable, toolLabel } from "@/features/flow/labels";
import type { Item, Step } from "@/features/live/state";
import { clip, useClock, useLiveFeed } from "@/features/live/use-live";
import { RESOURCES, ROLES } from "@/lib/game";
import { BOARD_CSS, Tile, Toolbar, useBoard, useEditing, useRotation, useStage, type Frame } from "./board";
import { countdown, instant, number, useOverview, type Command, type Overview, type Village } from "./data";
import { FlowGraph, chosen } from "./graph";
import { slideCards, type CardView } from "./highlights";
import { insightCards } from "./insights";
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

function VillageBody({ village, overview, now }: { village: Village; overview: Overview; now: number }) {
  const player = overview.player;
  const protection = instant(player?.protection_until);
  const since = village.synced_at ? (now - instant(village.synced_at)) / 3_600_000 : 0;
  const stock = (r: "wood" | "clay" | "iron") => Math.min(village.storage, village[r] + village[`${r}_prod`] * Math.max(0, since));
  return (
    <>
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
    </>
  );
}

function DecisionBody({ items }: { items: Item[] }) {
  const pick = chosen(items);
  if (!pick) return <span className="tw-secondary">nenhuma decisão nesta rodada ainda</span>;
  return (
    <div className="tw-decision">
      <div>
        <span className="tw-secondary">{agentLabel(pick.source)}</span>
        <strong>{clip(readable(pick.title), 44)}</strong>
        <span className="tw-secondary">{clip(readable(pick.note || pick.reason || ""), 70) || "—"}</span>
      </div>
      <span className="tw-state" data-status={pick.status}>
        {pick.status === "deferred" && /falta|dispon/i.test(pick.note) ? "Aguardando" : STATE_LABEL[pick.status]}
      </span>
    </div>
  );
}

function MovesBody({ overview, village, now }: { overview: Overview; village: Village; now: number }) {
  const commands = overview.commands.filter((c) => instant(c.arrival_at) > now).sort((a, b) => instant(a.arrival_at) - instant(b.arrival_at));
  const scavenging = village.scavenge.filter((s) => s.return_at && instant(s.return_at) > now);
  return (
    <ul className="tw-list">
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

function ActivityBody({ steps }: { steps: Step[] }) {
  return (
    <ol className="tw-events">
      {steps.slice(0, ACTIVITY).map((step) => (
        <li key={step.id} data-bad={step.ok === false || undefined}>
          <time>{time(step.at)}</time>
          <span>{clip(describe(step), 140)}</span>
        </li>
      ))}
      {!steps.length && <li className="tw-secondary">esperando o próximo passo…</li>}
    </ol>
  );
}

function Panel({ frame, cards, fixed }: { frame: Frame; cards: Record<string, CardView>; fixed: Record<string, ReactNode> }) {
  const members = frame.cards.filter((c) => cards[c] || fixed[c]);
  const index = useRotation(members.length);
  const id = members[index];
  if (!id) return <section className="tw-panel" />;
  if (fixed[id]) return <>{fixed[id]}</>;
  const card = cards[id];
  return (
    <section className={`tw-panel ${card.className ?? ""}`}>
      <header className="tw-head">
        <h2>{card.title}</h2>
        {members.length > 1 ? (
          <span className="tw-pager">
            {members.map((m, i) => (
              <i key={m} data-on={i === index || undefined} />
            ))}
          </span>
        ) : (
          card.aside
        )}
      </header>
      <div className="tw-body tw-slide" key={id}>
        {card.body}
      </div>
    </section>
  );
}

export function TwitchScreen({ only, since: sinceParam, transparent, edit, saved }: { only: number | null; since: string | null; transparent: boolean; edit: boolean; saved: string | null }) {
  const { state } = useLiveFeed(only);
  const overview = useOverview();
  const now = useClock();
  const since = useSince(sinceParam);
  const scale = useStage();
  const [editing, setEditing] = useEditing(edit);
  const { board, selected, setSelected, select, moveBy, resize, group, ungroup, arrange, reset, link } = useBoard(saved);
  const village = overview?.villages.find((v) => only === null || v.id === only) ?? overview?.villages[0];
  const incoming = (overview?.commands ?? []).filter((c) => c.direction === "in" && instant(c.arrival_at) > now);
  const [x, y] = (village?.coords ?? "0|0").split("|").map(Number);

  const waiting: CardView = { title: "Carregando", body: <span className="tw-secondary">carregando…</span> };
  const cards: Record<string, CardView> = {
    village:
      village && overview
        ? {
            title: `Aldeia — ${village.name}`,
            aside: (
              <span className="tw-secondary">
                ({village.coords}) K{Math.floor(y / 100)}
                {Math.floor(x / 100)}
              </span>
            ),
            body: <VillageBody village={village} overview={overview} now={now} />,
          }
        : waiting,
    decision: { title: "Decisão atual", body: <DecisionBody items={state.items} /> },
    moves: village && overview ? { title: "Movimentos", body: <MovesBody overview={overview} village={village} now={now} />, className: "tw-moves" } : waiting,
    flow: { title: "Fluxo de decisões dos agentes", body: <FlowGraph specialists={state.specialists} items={state.items} thinking={state.phase === "thinking"} />, className: "tw-flow" },
    activity: { title: "Atividade ao vivo", body: <ActivityBody steps={state.steps} />, className: "tw-activity" },
    ...(village && overview ? slideCards({ overview, village, items: state.items, steps: state.steps, since, now }) : {}),
    ...(village && overview ? insightCards({ overview, village, nextReview: state.nextReview, since, now }) : {}),
  };
  const fixed: Record<string, ReactNode> = {
    header: <Header village={village} mode={state.mode} next={state.nextReview} now={now} incoming={incoming} />,
    game: <section className="tw-game" aria-label="janela do jogo (captura do OBS)" />,
  };

  return (
    <div className="tw-root" data-transparent={transparent || undefined} onPointerDown={() => editing && setSelected([])}>
      <style>{TWITCH_CSS + BOARD_CSS}</style>
      <div className="tw-stage" style={{ transform: `scale(${scale})` }}>
        {board.map((frame) => (
          <Tile key={frame.id} frame={frame} board={board} editing={editing} selected={selected} scale={scale} onSelect={select} onMove={moveBy} onResize={resize}>
            <Panel frame={frame} cards={cards} fixed={fixed} />
          </Tile>
        ))}
      </div>
      {editing && <Toolbar selected={selected} board={board} onGroup={group} onUngroup={ungroup} onArrange={arrange} onReset={reset} link={link} onClose={() => setEditing(false)} />}
    </div>
  );
}
