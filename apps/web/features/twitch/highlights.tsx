"use client";

import type { ReactNode } from "react";
import { agentLabel, readable, toolLabel } from "@/features/flow/labels";
import type { Item, Step } from "@/features/live/state";
import { clip } from "@/features/live/use-live";
import { BUILDINGS, RESOURCES } from "@/lib/game";
import { countdown, duration, instant, number, useKnobs, useNearby, useQuests, useRounds, useSession, useSocial, type Command, type Overview, type Village } from "./data";

const MAP_MIN_FIELDS = 3;

function Session({ since, village, now }: { since: number; village: Village; now: number }) {
  const { stats, snapshots, reports } = useSession(since);
  const first = snapshots.find((s) => instant(s.taken_at) >= since) ?? snapshots[0];
  const gained = first ? village.points - first.points : 0;
  const loot = reports.filter((r) => instant(r.received_at) >= since).reduce((sum, r) => sum + (r.haul_total ?? r.loot_wood + r.loot_clay + r.loot_iron), 0);
  const ok = stats?.actions_ok ?? 0;
  const failed = stats?.actions_failed ?? 0;
  return (
    <div className="tw-grid-2">
      <Metric label="pontos" value={`${gained >= 0 ? "+" : ""}${number(gained)}`} />
      <Metric label="saqueado" value={number(loot)} />
      <Metric label="obras" value={number(stats?.builds ?? 0)} />
      <Metric label="recrutadas" value={number(stats?.recruits ?? 0)} />
      <Metric label="ações certas" value={`${ok} / ${ok + failed}`} />
      <Metric label="no ar há" value={duration(now - since)} />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="tw-metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function Thinking({ items }: { items: Item[] }) {
  const lines = items.slice(0, 3).map((item) => {
    const what = readable(item.title);
    if (item.status === "deferred") return `Adiei ${what}: ${readable(item.note)}`;
    if (item.status === "failed") return `Tentei ${what}, o jogo recusou: ${readable(item.note)}`;
    const why = readable(item.reason || item.note || "");
    return `Escolhi ${what}${why ? ` porque ${why}` : ""}`;
  });
  if (!lines.length) return <p className="tw-muted">o coordenador ainda não decidiu nesta rodada</p>;
  return (
    <ul className="tw-lines">
      {lines.map((line, i) => (
        <li key={i}>{clip(line, 150)}</li>
      ))}
    </ul>
  );
}

function Learning({ steps, items }: { steps: Step[]; items: Item[] }) {
  const knobs = useKnobs();
  const rounds = useRounds();
  const last = [...knobs].filter((k) => k.updated_at).sort((a, b) => instant(b.updated_at) - instant(a.updated_at))[0];
  const change = last?.history[last.history.length - 1];
  const learned = rounds[0]?.data.learned;
  const bonus = Object.entries(learned?.bonus ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 4);
  const explored = items.find((i) => i.explored) ?? null;
  const repair = steps.find((s) => s.step === "repair");
  return (
    <div className="tw-learning">
      {last && change && (
        <p>
          <b>{clip(last.description, 42)}</b>: {Number(change.from.toFixed(2))} → {Number(change.to.toFixed(2))} <span className="tw-muted">({clip(change.why, 60)})</span>
        </p>
      )}
      <div className="tw-bars">
        {bonus.map(([source, value]) => (
          <div key={source} className="tw-bar-row">
            <span>{agentLabel(source)}</span>
            <span className="tw-bar">
              <span style={{ width: `${Math.min(100, (value / 2) * 100)}%` }} />
            </span>
            <b>{value.toFixed(2)}×</b>
          </div>
        ))}
      </div>
      {explored && <p className="tw-accent">✦ explorando: {readable(explored.title)}</p>}
      {repair && (
        <p>
          ↻ {toolLabel(repair.tool)}: o jogo disse “{clip(repair.text, 60)}”, corrigi para <code>{clip(repair.args, 40)}</code>
        </p>
      )}
    </div>
  );
}

function Builds({ village, now }: { village: Village; now: number }) {
  const queue = village.buildings.filter((b) => b.queued_until).sort((a, b) => instant(a.queued_until) - instant(b.queued_until));
  if (!queue.length) return <p className="tw-muted">fila de obras vazia</p>;
  return (
    <div className="tw-bars">
      {queue.slice(0, 3).map((b) => {
        const left = instant(b.queued_until) - now;
        const total = (b.build_time ?? 0) * 1000;
        const done = total > 0 ? Math.min(100, Math.max(0, (1 - left / total) * 100)) : 0;
        return (
          <div key={b.name} className="tw-bar-row">
            <span>
              {BUILDINGS[b.name] ?? b.label} → {b.queued_level}
            </span>
            <span className="tw-bar">
              <span style={{ width: `${done}%` }} />
            </span>
            <b className="tw-count">{countdown(instant(b.queued_until), now)}</b>
          </div>
        );
      })}
    </div>
  );
}

function Raid({ since }: { since: number }) {
  const { reports } = useSession(since);
  const last = reports[0];
  if (!last) return <p className="tw-muted">nenhum saque registrado ainda</p>;
  const haul = last.haul_total ?? last.loot_wood + last.loot_clay + last.loot_iron;
  return (
    <div className="tw-raid" data-result={last.result ?? "none"}>
      <span className="tw-raid-dot" />
      <div>
        <b>{last.target_coords ?? clip(last.title, 40)}</b>
        <p>
          trouxe <b>{number(haul)}</b> · {number(last.loot_wood)} madeira · {number(last.loot_clay)} argila · {number(last.loot_iron)} ferro
        </p>
      </div>
    </div>
  );
}

function Quests() {
  const quests = useQuests();
  const quest = quests.find((q) => q.state !== "done") ?? quests[0];
  if (!quest) return <p className="tw-muted">sem missões abertas</p>;
  return (
    <div>
      <b>{quest.title}</b>
      <div className="tw-bars">
        {quest.goals.slice(0, 3).map((g, i) => {
          const share = g.target ? Math.min(100, ((g.current ?? 0) / g.target) * 100) : 0;
          return (
            <div key={i} className="tw-bar-row">
              <span>{clip(g.title, 28)}</span>
              <span className="tw-bar">
                <span style={{ width: `${share}%` }} />
              </span>
              <b>
                {g.current ?? 0}/{g.target ?? "?"}
              </b>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Production({ since, village }: { since: number; village: Village }) {
  const { snapshots } = useSession(since);
  const points = snapshots.slice(-60);
  const top = Math.max(1, ...points.flatMap((s) => [s.wood, s.clay, s.iron]));
  const line = (key: "wood" | "clay" | "iron") => points.map((s, i) => `${(i / Math.max(1, points.length - 1)) * 100},${100 - (s[key] / top) * 100}`).join(" ");
  return (
    <div className="tw-chart">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none">
        {(["wood", "clay", "iron"] as const).map((key) => (
          <polyline key={key} points={line(key)} className={`tw-line-${key}`} vectorEffect="non-scaling-stroke" />
        ))}
      </svg>
      <div className="tw-legend">
        {(["wood", "clay", "iron"] as const).map((key) => (
          <span key={key} className={`tw-legend-${key}`}>
            {RESOURCES[key].label} +{number(village[`${key}_prod`])}/h
          </span>
        ))}
      </div>
    </div>
  );
}

function progress(command: Command, now: number, distance: number): number {
  const minutes = /explor|espi/i.test(command.label) ? 9 * distance : 18 * distance;
  const left = (instant(command.arrival_at) - now) / 60_000;
  return Math.min(1, Math.max(0, 1 - left / Math.max(1, minutes)));
}

function MiniMap({ village, commands, now }: { village: Village; commands: Command[]; now: number }) {
  const nearby = useNearby(village.id);
  const [ox, oy] = village.coords.split("|").map(Number);
  const reach = Math.max(MAP_MIN_FIELDS, ...nearby.map((n) => { const [x, y] = n.coords.split("|").map(Number); return Math.max(Math.abs(x - ox) / 2, Math.abs(y - oy)); }));
  const place = (coords: string) => {
    const [x, y] = coords.split("|").map(Number);
    return { x: 100 + ((x - ox) / reach) * 90, y: 50 + ((y - oy) / reach) * 44 };
  };
  const moving = commands.filter((c) => c.coords && c.direction !== "in");
  return (
    <svg className="tw-map" viewBox="0 0 200 100" preserveAspectRatio="xMidYMid meet">
      {nearby.map((n) => {
        const p = place(n.coords);
        return <circle key={n.id} cx={p.x} cy={p.y} r={n.is_barbarian ? 1.8 : 2.4} className={n.is_barbarian ? "tw-map-barb" : "tw-map-player"} />;
      })}
      {moving.map((c, i) => {
        const p = place(c.coords!);
        const [cx, cy] = c.coords!.split("|").map(Number);
        const distance = Math.hypot(cx - ox, cy - oy);
        const t = progress(c, now, distance);
        const back = c.direction === "return";
        const x = back ? p.x + (100 - p.x) * t : 100 + (p.x - 100) * t;
        const y = back ? p.y + (50 - p.y) * t : 50 + (p.y - 50) * t;
        return (
          <g key={i}>
            <line x1={100} y1={50} x2={p.x} y2={p.y} className="tw-map-route" />
            <circle cx={x} cy={y} r={2.2} className="tw-map-troop" />
          </g>
        );
      })}
      <circle cx={100} cy={50} r={3.2} className="tw-map-own" />
    </svg>
  );
}

function Social() {
  const { mails, decisions } = useSocial();
  const sorted = [...mails].sort((a, b) => (a.data.unread === b.data.unread ? 0 : a.data.unread ? -1 : 1));
  const sent = mails.find((m) => m.data.answered);
  const received = sorted[0];
  const tribe = decisions.find((d) => d.action === "apply_to_tribe");
  const friend = decisions.find((d) => d.action === "add_friend" || d.action === "accept_friend");
  return (
    <ul className="tw-lines">
      {received && <li>✉ recebida: <b>{clip(received.data.subject ?? received.title, 40)}</b> <span className="tw-muted">de {received.data.sender}</span></li>}
      {sent && <li>↗ respondida: <b>{clip(sent.data.subject ?? sent.title, 40)}</b> <span className="tw-muted">para {sent.data.sender}</span></li>}
      {tribe && <li>⚑ tribo: {clip(readable(tribe.result), 70)}</li>}
      {friend && <li>☺ amizade: {clip(readable(friend.result), 70)}</li>}
      {!received && !sent && !tribe && !friend && <li className="tw-muted">nenhuma conversa ainda</li>}
    </ul>
  );
}

function Protection({ until, now }: { until: number; now: number }) {
  const left = until - now;
  if (left <= 0) return <p className="tw-muted">proteção de iniciante terminou</p>;
  return (
    <div className="tw-protection" data-close={left < 86_400_000 || undefined}>
      <strong className="tw-count">{countdown(until, now)}</strong>
      <span>até o fim da proteção de iniciante</span>
    </div>
  );
}

export type CardView = { title: string; aside?: ReactNode; body: ReactNode; className?: string };

export function slideCards({ overview, village, items, steps, since, now }: { overview: Overview; village: Village; items: Item[]; steps: Step[]; since: number; now: number }): Record<string, CardView> {
  const until = instant(overview.player?.protection_until);
  return {
    session: { title: "Resumo da sessão", body: <Session since={since} village={village} now={now} /> },
    thinking: { title: "Pensamento da IA", body: <Thinking items={items} /> },
    learning: { title: "Aprendizado", body: <Learning steps={steps} items={items} /> },
    builds: { title: "Obras", body: <Builds village={village} now={now} /> },
    map: { title: "Mapa ao redor", body: <MiniMap village={village} commands={overview.commands} now={now} /> },
    raid: { title: "Último saque", body: <Raid since={since} /> },
    quests: { title: "Missões", body: <Quests /> },
    production: { title: "Estoque nas últimas horas", body: <Production since={since} village={village} /> },
    social: { title: "Social", body: <Social /> },
    protection: { title: "Proteção de iniciante", body: until ? <Protection until={until} now={now} /> : <p className="tw-muted">sem proteção</p> },
  };
}
