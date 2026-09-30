"use client";

import { readable } from "@/features/flow/labels";
import { clip } from "@/features/live/use-live";
import { BUILDINGS, UNITS } from "@/lib/game";
import { countdown, duration, instant, number, useChallenges, useHistory, useNearby, useRecentLoot, useRounds, useStats, useWatch, type Overview, type Village } from "./data";
import type { CardView } from "./highlights";

const AGENDA_SIZE = 7;
const HISTORY_HOURS = 12;
const NEIGHBOURS = 5;

type Event = { at: number; icon: string; text: string };

function Agenda({ overview, village, nextReview, now }: { overview: Overview; village: Village; nextReview: number | null; now: number }) {
  const rounds = useRounds();
  const round = rounds.find((r) => r.village_id === village.id);
  const events: Event[] = [];
  for (const b of village.buildings) if (b.queued_until) events.push({ at: instant(b.queued_until), icon: "🏗", text: `${BUILDINGS[b.name] ?? b.label} ${b.queued_level} fica pronto` });
  for (const o of village.recruit_orders ?? []) if (o.finishes_at) events.push({ at: instant(o.finishes_at), icon: "⚔", text: `${o.count} ${(UNITS[o.unit] ?? o.unit).toLowerCase()} recrutados` });
  for (const s of village.scavenge) if (s.return_at) events.push({ at: instant(s.return_at), icon: "⛏", text: `${s.name.toLowerCase()} volta` });
  for (const c of overview.commands) events.push({ at: instant(c.arrival_at), icon: c.direction === "in" ? "⚠" : "→", text: `${c.label || c.kind}${c.direction === "in" ? " chega" : ""}` });
  const created = round ? instant(round.created_at) : now;
  for (const d of round?.data.deferred ?? []) {
    if (d.ready_in_hours && d.ready_in_hours > 0) events.push({ at: created + d.ready_in_hours * 3_600_000, icon: "💰", text: `${readable(d.title)} cabe no estoque` });
  }
  if (nextReview) events.push({ at: nextReview, icon: "↻", text: "próxima rodada" });
  const protection = instant(overview.player?.protection_until);
  if (protection) events.push({ at: protection, icon: "🛡", text: "fim da proteção de iniciante" });

  const upcoming = events.filter((e) => e.at > now).sort((a, b) => a.at - b.at).filter((e, i, all) => all.findIndex((o) => o.text === e.text) === i).slice(0, AGENDA_SIZE);
  if (!upcoming.length) return <p className="tw-muted">nada agendado</p>;
  return (
    <ul className="tw-agenda">
      {upcoming.map((e, i) => (
        <li key={i}>
          <span className="tw-agenda-icon">{e.icon}</span>
          <span className="tw-truncate">{clip(e.text, 60)}</span>
          <b className="tw-count">{countdown(e.at, now)}</b>
        </li>
      ))}
    </ul>
  );
}

function Blockers({ village }: { village: Village }) {
  const rounds = useRounds();
  const watch = useWatch();
  const round = rounds.find((r) => r.village_id === village.id);
  const reasons = new Map<string, number>();
  for (const d of round?.data.deferred ?? []) {
    const why = readable(d.why ?? "").replace(/\d[\d.,]*/g, "N").replace(/disponível em ~Nh/, "").trim();
    const kind = /reservad/.test(why) ? `recurso guardado: ${why.split("para ").pop()}` : /faltam/.test(why) ? "falta recurso" : /fila/.test(why) ? "fila de obras cheia" : /aprendido|requisito/.test(why) ? "requisito do jogo" : clip(why, 40);
    reasons.set(kind, (reasons.get(kind) ?? 0) + 1);
  }
  const held = round?.data.budget?.reservations?.filter((r) => r.purpose !== "base" && Object.keys(r.cost ?? {}).length) ?? [];
  return (
    <div className="tw-learning">
      {[...reasons.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([why, count]) => (
        <p key={why}>
          <b>{count}×</b> {why}
        </p>
      ))}
      {held.length > 0 && <p className="tw-muted">reservando para: {held.map((r) => r.purpose).join(", ")}</p>}
      {watch[0] && <p className="tw-accent">vigia: {clip(watch[0].text, 90)}</p>}
      {!reasons.size && !held.length && <p className="tw-muted">nada travado agora</p>}
    </div>
  );
}

function Points({ village }: { village: Village }) {
  const history = useHistory(HISTORY_HOURS);
  const points = history.map((s) => s.points);
  if (points.length < 2) return <p className="tw-muted">sem histórico ainda</p>;
  const low = Math.min(...points);
  const high = Math.max(...points, low + 1);
  const line = points.map((p, i) => `${(i / (points.length - 1)) * 100},${100 - ((p - low) / (high - low)) * 90 - 5}`).join(" ");
  return (
    <div className="tw-chart">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none">
        <polyline points={line} className="tw-line-points" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="tw-legend">
        <span>
          {number(points[0])} → <b>{number(village.points)}</b> pts em {HISTORY_HOURS}h
        </span>
        <span className="tw-count">+{number(village.points - points[0])}</span>
      </div>
    </div>
  );
}

function Pace({ since, now }: { since: number; now: number }) {
  const hours = Math.max(1, Math.ceil((now - since) / 3_600_000));
  const stats = useStats(hours);
  if (!stats) return <p className="tw-muted">carregando…</p>;
  const done = stats.actions_ok + stats.actions_failed + stats.actions_refused;
  const lastHour = stats.hourly.at(-1);
  const perHour = lastHour ? Object.values(lastHour.by_agent).reduce((a, b) => a + b, 0) : 0;
  return (
    <div className="tw-grid-2">
      <div className="tw-metric"><span>ações/hora</span><strong>{perHour}</strong></div>
      <div className="tw-metric"><span>acerto</span><strong>{done ? Math.round((stats.actions_ok / done) * 100) : 0}%</strong></div>
      <div className="tw-metric"><span>rodadas</span><strong>{stats.runs}</strong></div>
      <div className="tw-metric"><span>saques</span><strong>{stats.attacks}</strong></div>
      <div className="tw-metric"><span>tokens IA</span><strong>{number((stats.tokens_in + stats.tokens_out) / 1000)}k</strong></div>
      <div className="tw-metric"><span>janela</span><strong>{duration(now - since)}</strong></div>
    </div>
  );
}

function Income({ village, now }: { village: Village; now: number }) {
  const loot = useRecentLoot(1);
  const produced = village.wood_prod + village.clay_prod + village.iron_prod;
  const since = village.synced_at ? (now - instant(village.synced_at)) / 3_600_000 : 0;
  const stock = (r: "wood" | "clay" | "iron") => Math.min(village.storage, village[r] + village[`${r}_prod`] * Math.max(0, since));
  const hoursFull = Math.min(
    ...(["wood", "clay", "iron"] as const).map((r) => (village[`${r}_prod`] ? (village.storage - stock(r)) / village[`${r}_prod`] : Infinity)),
  );
  return (
    <div className="tw-grid-2">
      <div className="tw-metric"><span>produção/h</span><strong>{number(produced)}</strong></div>
      <div className="tw-metric"><span>saque última hora</span><strong>{number(loot)}</strong></div>
      <div className="tw-metric"><span>total/h</span><strong>{number(produced + loot)}</strong></div>
      <div className="tw-metric" data-alert={hoursFull < 1 || undefined}>
        <span>armazém enche</span>
        <strong>{Number.isFinite(hoursFull) ? (hoursFull <= 0 ? "cheio" : countdown(now + hoursFull * 3_600_000, now)) : "—"}</strong>
      </div>
    </div>
  );
}

function Neighbours({ village }: { village: Village }) {
  const nearby = useNearby(village.id, "player");
  const players = nearby.filter((n) => !n.is_barbarian).sort((a, b) => b.points - a.points).slice(0, NEIGHBOURS);
  if (!players.length) return <p className="tw-muted">nenhum jogador por perto</p>;
  return (
    <ul className="tw-agenda">
      {players.map((p) => (
        <li key={p.id} data-alert={p.points > village.points * 2 || undefined}>
          <span className="tw-agenda-icon">{p.points > village.points * 2 ? "⚠" : "•"}</span>
          <span className="tw-truncate">
            {p.player_name ?? "?"} <span className="tw-secondary">{p.coords}</span>
          </span>
          <b>{number(p.points)}</b>
          <span className="tw-secondary">{p.distance.toFixed(1)} campos</span>
        </li>
      ))}
    </ul>
  );
}

function Achievements() {
  const items = useChallenges();
  const next = items.filter((c) => !c.done && c.status !== "blocked" && c.target).sort((a, b) => b.ratio - a.ratio).slice(0, 3);
  if (!next.length) return <p className="tw-muted">sem conquistas próximas</p>;
  return (
    <div className="tw-bars">
      {next.map((c) => (
        <div key={`${c.group}-${c.name}`} className="tw-bar-row">
          <span>{clip(c.name, 26)}</span>
          <span className="tw-bar">
            <span style={{ width: `${Math.min(100, c.ratio * 100)}%` }} />
          </span>
          <b>
            {number(c.current ?? 0)}/{number(c.target ?? 0)}
          </b>
        </div>
      ))}
    </div>
  );
}

export function insightCards({ overview, village, nextReview, since, now }: { overview: Overview; village: Village; nextReview: number | null; since: number; now: number }): Record<string, CardView> {
  return {
    agenda: { title: "Agenda da aldeia", body: <Agenda overview={overview} village={village} nextReview={nextReview} now={now} /> },
    blockers: { title: "O que está travando", body: <Blockers village={village} /> },
    points: { title: "Pontos nas últimas horas", body: <Points village={village} /> },
    pace: { title: "Ritmo do bot", body: <Pace since={since} now={now} /> },
    income: { title: "Renda e armazém", body: <Income village={village} now={now} /> },
    neighbours: { title: "Vizinhos", body: <Neighbours village={village} /> },
    achievements: { title: "Próximas conquistas", body: <Achievements /> },
  };
}
