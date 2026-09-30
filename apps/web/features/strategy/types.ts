import { BUILDINGS } from "@/lib/game";

export type Cost = Partial<Record<"wood" | "clay" | "stone" | "iron" | "pop", number>>;

export type Entry = {
  key?: string;
  source?: string;
  action?: string;
  title?: string;
  arguments?: Record<string, unknown>;
  reason?: string;
  expected_benefit?: string;
  priority?: number;
  cost?: Cost;
  troops?: Record<string, number>;
  horizon?: string;
  deadline?: string | null;
  confidence?: number;
  risks?: string[];
  purpose?: string;
  why?: string;
  ready_in_hours?: number | null;
  ok?: boolean;
  result?: string;
};

export type Reservation = { purpose: string; kind: string; reason: string; cost: Cost; troops?: Record<string, number> };

export type Constraint = { kind?: string; reason: string; source?: string; until?: string | null; blocks?: string[] };

export type Insight = { key?: string; text: string; certainty: string; age_hours: number; weight: number; confidence?: number; source?: string };

export type Budget = { stock?: Cost; held?: Cost; free?: Cost; reservations?: Reservation[]; troops_committed?: Record<string, number> };

export type Exploration = { title?: string; instead_of?: string; priority?: number; instead_priority?: number; rate?: number; reason?: string };

export type Learned = { bonus?: Record<string, number>; explore_rate?: number; streak?: number; repeated?: boolean };

export type RoundData = {
  role?: string;
  mode?: string;
  goal?: string;
  next_action?: Entry | null;
  executed?: Entry[];
  deferred?: Entry[];
  constraints?: Constraint[];
  budget?: Budget;
  insights?: Insight[];
  exploration?: Exploration | null;
  learned?: Learned | null;
};

export const HORIZON: Record<string, string> = { immediate: "imediato", tactical: "tático", strategic: "estratégico" };

export const CERTAINTY: Record<string, { label: string; tone: "success" | "neutral" | "warning" }> = {
  fact: { label: "fato", tone: "success" },
  estimate: { label: "estimativa", tone: "neutral" },
  hypothesis: { label: "hipótese", tone: "warning" },
};

export function purposeLabel(purpose: string): string {
  if (purpose === "base") return "reserva mínima";
  if (purpose === "expansion") return "expansão (nobre)";
  if (purpose === "defense") return "defesa";
  if (purpose.startsWith("plan:")) {
    const items = purpose.slice(5).split(",").map((b) => BUILDINGS[b.trim()] ?? b.trim()).filter(Boolean);
    return `plano: ${items.join(", ")}`;
  }
  return purpose.replace(/_/g, " ");
}
