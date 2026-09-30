"use client";

import { useEffect, useState } from "react";
import { useEvents } from "@/features/agents/events";

export type Building = { name: string; label: string; level: number; queued_level: number | null; queued_until: string | null; build_time: number | null };
export type Unit = { name: string; home: number; total: number; away: number };
export type Scavenge = { option_id: number; name: string; return_at: string | null };
export type Village = {
  id: number;
  name: string;
  coords: string;
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
  scavenge: Scavenge[];
  recruit_orders?: { unit: string; count: number; finishes_at: string | null }[];
};
export type Player = { points: number; rank: number | null; incomings: number; protection_until: string | null };
export type Command = { village_coords: string; direction: string; kind: string; label: string; coords: string | null; arrival_at: string };
export type Overview = { player: Player | null; villages: Village[]; commands: Command[] };
export type Snapshot = { taken_at: string; points: number; wood: number; clay: number; iron: number; storage: number };
export type Report = { title: string; category: string; result: string | null; received_at: string; target_coords: string | null; loot_wood: number; loot_clay: number; loot_iron: number; haul_total: number | null };
export type Goal = { title: string; current: number | null; target: number | null };
export type Quest = { title: string; state: string; goals: Goal[] };
export type Knob = { name: string; description: string; value: number; updated_at: string | null; reason: string; history: { at: string; from: number; to: number; why: string }[] };
export type Stats = { runs: number; actions_ok: number; actions_failed: number; actions_refused: number; builds: number; recruits: number; attacks: number; tokens_in: number; tokens_out: number; hourly: { hour: string; by_agent: Record<string, number> }[] };
export type Challenge = { name: string; group: string; current: number | null; target: number | null; ratio: number; done: boolean; status: string; agent: string };
export type WatchNote = { key: string; title: string; text: string; data: { purpose?: string } };
export type Nearby = { id: number; coords: string; points: number; distance: number; is_barbarian: boolean; player_name: string | null; travel_minutes: Record<string, number> };
export type Mail = { title: string; data: { subject?: string; sender?: string; messages?: { author: string; date: string }[]; answered?: boolean; unread?: boolean } };
export type Decision = { agent: string; action: string; ok: boolean; dry_run: boolean; result: string; arguments: Record<string, unknown>; created_at: string };
export type Learned = { bonus?: Record<string, number>; explore_rate?: number; streak?: number; repeated?: boolean };
export type Deferred = { key: string; source: string; action: string; title: string; why?: string; ready_in_hours?: number | null };
export type Round = {
  village_id: number;
  created_at: string;
  next_review_at: string | null;
  data: { learned?: Learned; exploration?: { title?: string; instead_of?: string; reason?: string } | null; deferred?: Deferred[]; budget?: { reservations?: { purpose: string; cost: Record<string, number> }[] } };
};

async function get<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(path);
    return response.ok ? ((await response.json()) as T) : fallback;
  } catch {
    return fallback;
  }
}

function useRefreshing<T>(load: () => Promise<T>, fallback: T, every: number, kinds: string[]): T {
  const [value, setValue] = useState<T>(fallback);
  const [tick, setTick] = useState(0);

  useEvents((event) => {
    if (kinds.includes(event.kind) || (event.kind === "flow" && kinds.includes("flow") && event.data.phase === "done")) setTick((t) => t + 1);
  });

  useEffect(() => {
    let alive = true;
    load().then((v) => alive && setValue(v));
    const timer = setTimeout(() => setTick((t) => t + 1), every);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [tick]);

  return value;
}

export function useOverview(): Overview | null {
  return useRefreshing(() => get<Overview | null>("/api/v1/game/overview", null), null, 60_000, ["sync", "flow"]);
}

export function useSession(since: number) {
  const hours = () => Math.max(1, Math.ceil((Date.now() - since) / 3_600_000));
  return useRefreshing(
    async () => {
      const [stats, snapshots, reports] = await Promise.all([
        get<Stats | null>(`/api/v1/agents/stats?hours=${hours()}`, null),
        get<Snapshot[]>(`/api/v1/game/history?hours=${hours()}`, []),
        get<{ items: Report[] }>("/api/v1/game/reports?category=attack&limit=50", { items: [] }),
      ]);
      return { stats, snapshots, reports: reports.items };
    },
    { stats: null as Stats | null, snapshots: [] as Snapshot[], reports: [] as Report[] },
    120_000,
    ["run_finished", "sync"],
  );
}

export function useQuests(): Quest[] {
  return useRefreshing(async () => (await get<{ quests: Quest[] }>("/api/v1/agents/quests", { quests: [] })).quests, [], 300_000, ["sync"]);
}

export function useKnobs(): Knob[] {
  return useRefreshing(() => get<Knob[]>("/api/v1/knobs", []), [], 600_000, []);
}

export function useRounds(): Round[] {
  return useRefreshing(() => get<Round[]>("/api/v1/agents/coordination", []), [], 120_000, ["flow"]);
}

export function useNearby(villageId: number | null, kind: "barbarian" | "player" | "all" = "all"): Nearby[] {
  const [value, setValue] = useState<Nearby[]>([]);
  useEffect(() => {
    if (villageId === null) return;
    get<Nearby[]>(`/api/v1/world/nearby?village_id=${villageId}&kind=${kind}&radius=15&limit=120`, []).then(setValue);
  }, [villageId, kind]);
  return value;
}

export function useSocial() {
  return useRefreshing(
    async () => {
      const [mails, decisions] = await Promise.all([get<Mail[]>("/api/v1/agents/lessons?topic=mail&limit=20", []), get<Decision[]>("/api/v1/agents/decisions?limit=200", [])]);
      return { mails, decisions: decisions.filter((d) => !d.dry_run) };
    },
    { mails: [] as Mail[], decisions: [] as Decision[] },
    300_000,
    ["run_finished"],
  );
}

export function useChallenges(): Challenge[] {
  return useRefreshing(async () => (await get<{ items: Challenge[] }>("/api/v1/challenges", { items: [] })).items, [], 600_000, []);
}

export function useWatch(): WatchNote[] {
  return useRefreshing(() => get<WatchNote[]>("/api/v1/agents/lessons?topic=watch&limit=5", []), [], 300_000, ["flow"]);
}

export function useHistory(hours: number): Snapshot[] {
  return useRefreshing(() => get<Snapshot[]>(`/api/v1/game/history?hours=${hours}`, []), [], 300_000, ["sync"]);
}

export function useStats(hours: number): Stats | null {
  return useRefreshing(() => get<Stats | null>(`/api/v1/agents/stats?hours=${hours}`, null), null, 120_000, ["run_finished"]);
}

export function useRecentLoot(hours: number): number {
  return useRefreshing(
    async () => {
      const since = Date.now() - hours * 3_600_000;
      const { items } = await get<{ items: Report[] }>("/api/v1/game/reports?category=attack&limit=50", { items: [] });
      return items.filter((r) => instant(r.received_at) >= since).reduce((sum, r) => sum + (r.haul_total ?? r.loot_wood + r.loot_clay + r.loot_iron), 0);
    },
    0,
    300_000,
    ["sync"],
  );
}

export function instant(text: string | null | undefined): number {
  if (!text) return 0;
  const zoned = /[zZ]|[+-]\d\d:?\d\d$/.test(text) ? text : `${text}Z`;
  return Date.parse(zoned) || 0;
}

export function countdown(until: number, now: number): string {
  const s = Math.max(0, Math.round((until - now) / 1000));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const two = (n: number) => String(n).padStart(2, "0");
  if (h >= 24) return `${Math.floor(h / 24)}d ${h % 24}h`;
  return h ? `${h}:${two(m)}:${two(s % 60)}` : `${m}:${two(s % 60)}`;
}

export function duration(ms: number): string {
  const m = Math.max(0, Math.floor(ms / 60_000));
  return m < 60 ? `${m}min` : `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}min`;
}

export function number(n: number): string {
  return Math.floor(n).toLocaleString("pt-BR");
}
