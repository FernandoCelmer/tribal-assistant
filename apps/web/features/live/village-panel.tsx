"use client";

import { useEffect, useState } from "react";
import { useEvents } from "@/features/agents/events";
import { BUILDINGS, RESOURCES, UNITS, type Resource } from "@/lib/game";
import { instant } from "./state";

type Building = { name: string; label: string; level: number; queued_level: number | null; queued_until: string | null };
type Unit = { name: string; home: number; total: number; away: number };
type Order = { unit: string; count: number; finishes_at: string | null };
type Scavenge = { option_id: number; name: string; is_locked: boolean; return_at: string | null };
type Village = {
  id: number;
  name: string;
  points: number;
  wood: number;
  clay: number;
  iron: number;
  storage: number;
  pop_current: number;
  pop_max: number;
  wood_prod: number;
  clay_prod: number;
  iron_prod: number;
  synced_at: string | null;
  buildings: Building[];
  units: Unit[];
  recruit_orders: Order[];
  scavenge: Scavenge[];
};
type Player = { points: number; rank: number | null; incomings: number; protection_until: string | null; new_reports: number; new_mails: number };
type Command = { direction: string; kind: string; label: string; coords: string | null; arrival_at: string };
type Report = { title: string; received_at: string };
type Overview = { player: Player | null; villages: Village[]; commands: Command[]; reports: Report[] };

const REFRESH = 60_000;
const ORDER: Resource[] = ["wood", "clay", "iron"];

function left(until: number, now: number): string {
  const s = Math.max(0, Math.round((until - now) / 1000));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const two = (n: number) => String(n).padStart(2, "0");
  if (h >= 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
  return h ? `${h}:${two(m)}:${two(sec)}` : `${m}:${two(sec)}`;
}

function number(n: number): string {
  return Math.floor(n).toLocaleString("pt-BR");
}

export function VillagePanel({ only, now, nextReview }: { only: number | null; now: number; nextReview: number | null }) {
  const [data, setData] = useState<Overview | null>(null);
  const [tick, setTick] = useState(0);

  useEvents((event) => {
    if (event.kind === "sync" || (event.kind === "flow" && event.data.phase === "done")) setTick((t) => t + 1);
  });

  useEffect(() => {
    let alive = true;
    fetch("/api/v1/game/overview")
      .then((r) => (r.ok ? r.json() : null))
      .then((d: Overview | null) => alive && d && setData(d))
      .catch(() => undefined);
    const timer = setTimeout(() => setTick((t) => t + 1), REFRESH);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [tick]);

  const village = data?.villages.find((v) => only === null || v.id === only) ?? data?.villages[0];
  if (!village) return <aside className="live-side"><div className="live-cap">Aldeia</div><div className="live-block live-dim">carregando…</div></aside>;

  const since = village.synced_at ? (now - instant(village.synced_at)) / 3_600_000 : 0;
  const stock = (r: Resource) => Math.min(village.storage, village[r] + village[`${r}_prod` as const] * Math.max(0, since));
  const queue = village.buildings.filter((b) => b.queued_until).sort((a, b) => instant(a.queued_until!) - instant(b.queued_until!));
  const troops = village.units.filter((u) => u.total > 0);
  const scavenging = village.scavenge.filter((s) => s.return_at && instant(s.return_at) > now);
  const commands = (data?.commands ?? []).filter((c) => instant(c.arrival_at) > now).sort((a, b) => instant(a.arrival_at) - instant(b.arrival_at));
  const incoming = commands.filter((c) => c.direction === "incoming");
  const player = data?.player;
  const protection = player?.protection_until ? instant(player.protection_until) : null;
  const report = data?.reports[0];

  return (
    <aside className="live-side">
      <div className="live-cap">{village.name}</div>
      <div className="live-block">
        <div className="live-cap">Jogador</div>
        <div className="live-row">
          <span>
            <b>{number(player?.points ?? village.points)}</b> <span className="live-dim">pts</span>
          </span>
          {player?.rank ? <span className="live-dim">#{number(player.rank)}</span> : null}
          {protection && protection > now && <span className="live-chip">proteção {left(protection, now)}</span>}
        </div>
        {nextReview && (
          <div className="live-row live-dim">
            próxima rodada <b className="live-count">{nextReview > now ? left(nextReview, now) : "agora"}</b>
          </div>
        )}
      </div>

      <div className="live-block">
        <div className="live-cap">Recursos · armazém {number(village.storage)}</div>
        {ORDER.map((r) => {
          const value = stock(r);
          return (
            <div key={r} className="live-res">
              <img src={RESOURCES[r].icon} alt="" width={16} height={16} />
              <span className="live-res-value">{number(value)}</span>
              <span className="live-dim">+{number(village[`${r}_prod` as const])}/h</span>
              <span className="live-bar">
                <span style={{ width: `${Math.min(100, (value / village.storage) * 100)}%`, background: `var(--${r})` }} />
              </span>
            </div>
          );
        })}
        <div className="live-res">
          <span className="live-res-icon">👥</span>
          <span className="live-res-value">{number(village.pop_current)}</span>
          <span className="live-dim">/ {number(village.pop_max)}</span>
          <span className="live-bar">
            <span style={{ width: `${Math.min(100, (village.pop_current / Math.max(1, village.pop_max)) * 100)}%`, background: "var(--live-pending)" }} />
          </span>
        </div>
      </div>

      <div className="live-block">
        <div className="live-cap">Obras {queue.length ? `· ${queue.length} na fila` : "· fila vazia"}</div>
        {queue.slice(0, 3).map((b) => (
          <div key={b.name} className="live-row">
            <span>
              {BUILDINGS[b.name] ?? b.label} <span className="live-dim">→ {b.queued_level}</span>
            </span>
            <b className="live-count">{left(instant(b.queued_until!), now)}</b>
          </div>
        ))}
        {village.recruit_orders.slice(0, 2).map((o, i) => (
          <div key={`${o.unit}-${i}`} className="live-row">
            <span>
              {o.count}× {(UNITS[o.unit] ?? o.unit).toLowerCase()}
            </span>
            {o.finishes_at && <b className="live-count">{left(instant(o.finishes_at), now)}</b>}
          </div>
        ))}
      </div>

      <div className="live-block">
        <div className="live-cap">Tropas</div>
        <div className="live-troops">
          {troops.map((u) => (
            <span key={u.name}>
              {(UNITS[u.name] ?? u.name).toLowerCase()} <b>{u.home}</b>
              {u.away > 0 && <span className="live-dim">+{u.away} fora</span>}
            </span>
          ))}
          {!troops.length && <span className="live-dim">nenhuma</span>}
        </div>
      </div>

      <div className="live-block">
        <div className="live-cap">
          Movimentos
          {incoming.length > 0 && <span className="live-bad"> · {incoming.length} ataque(s) chegando</span>}
        </div>
        {commands.slice(0, 2).map((c, i) => (
          <div key={i} className="live-row">
            <span>
              {c.direction === "incoming" ? "⚠ " : "→ "}
              {c.label || c.kind} {c.coords && <span className="live-dim">{c.coords}</span>}
            </span>
            <b className="live-count">{left(instant(c.arrival_at), now)}</b>
          </div>
        ))}
        {scavenging.slice(0, 2).map((s) => (
          <div key={s.option_id} className="live-row">
            <span>{s.name.toLowerCase()}</span>
            <b className="live-count">{left(instant(s.return_at!), now)}</b>
          </div>
        ))}
        {!commands.length && !scavenging.length && <div className="live-dim">nada em trânsito</div>}
      </div>

      {report && (
        <div className="live-block">
          <div className="live-cap">Último relatório</div>
          <div className="live-clip">{report.title}</div>
        </div>
      )}
    </aside>
  );
}

export const SIDE_CSS = `
.live-side { position: absolute; top: 72px; right: 12px; bottom: 12px; width: 328px; font-size: 13px; display: flex; flex-direction: column; }
.live-block { display: flex; flex-direction: column; gap: 5px; padding: 0 14px 10px; border-bottom: 1px solid var(--live-line); }
.live-block:last-child { border-bottom: 0; }
.live-block > .live-cap { margin: 0 -14px 4px; min-height: 34px; border-bottom: 0; padding-top: 4px; font-size: 12px; color: var(--live-dim); font-weight: 500; }
.live-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; white-space: nowrap; }
.live-row > span { overflow: hidden; text-overflow: ellipsis; }
.live-count { font-variant-numeric: tabular-nums; color: var(--live-running); font-weight: 600; }
.live-chip { font-size: 11px; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--live-line); color: var(--live-ok); }
.live-res { display: grid; grid-template-columns: 18px 64px 70px 1fr; align-items: center; gap: 6px; font-variant-numeric: tabular-nums; }
.live-res-value { font-weight: 600; }
.live-res-icon { font-size: 12px; }
.live-bar { height: 5px; border-radius: 3px; background: var(--live-line); overflow: hidden; }
.live-bar > span { display: block; height: 100%; border-radius: 3px; transition: width 1s linear; }
.live-troops { display: flex; flex-wrap: wrap; gap: 4px 12px; }
.live-troops b { margin-left: 3px; }
.live-troops .live-dim { margin-left: 4px; font-size: 11px; }
.live-clip { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--live-dim); }
`;
