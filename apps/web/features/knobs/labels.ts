import type { Schemas } from "@/lib/api";
import { ROLES } from "@/lib/game";

type Knob = Schemas["KnobOut"];

const LABELS: Record<string, string> = {
  base_stock_share: "Reserva mínima do estoque",
  filler_wait_hours: "Espera antes de obra encaixe",
  scavenge_share: "Lanceiros na coleta",
};

const AREAS: Record<string, string> = {
  account: "Conta", capacity: "Capacidade", conquest: "Conquista", cooldown: "Intervalo", coordinator: "Coordenador",
  defense: "Defesa", diplomacy: "Diplomacia", dodge: "Esquiva", economy: "Economia", expansion: "Expansão", farm: "Fazenda",
  intel: "Inteligência", iron_parking: "Ferro no mercado", items: "Itens", knight: "Paladino", learning: "Aprendizado",
  logistics: "Logística", market: "Mercado", noble: "Nobre", pacing: "Ritmo das obras", plan: "Plano automático",
  plan_reserve: "Reserva do plano", policy: "Política do papel", quest: "Missões", raid: "Saque", recruit: "Recrutamento",
  role: "Troca de papel", scavenge: "Coleta", social: "Social", spy: "Exploradores", storage: "Armazém", threat: "Ameaça",
  weight: "Peso na prioridade",
};

const TERMS: Record<string, string> = {
  risk_avoided: "risco evitado", opportunity_cost: "custo de oportunidade", urgency: "urgência", impact: "impacto",
  opportunity: "oportunidade", uncertainty: "incerteza",
};

function translate(text: string): string {
  return text
    .replace(/\b(risk_avoided|opportunity_cost|urgency|impact|opportunity|uncertainty)\b/g, (t) => TERMS[t] ?? t)
    .replace(/\bpapel (growth|defense|offensive|support|expansion|emergency)\b/g, (_, r: string) => `papel ${(ROLES[r] ?? r).toLowerCase()}`)
    .replace(/_/g, " ");
}

function capital(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function knobLabel(knob: Pick<Knob, "name" | "description">): string {
  if (LABELS[knob.name]) return LABELS[knob.name];
  if (knob.description) return capital(translate(knob.description));
  return capital(translate(knob.name.split(".").pop() ?? knob.name));
}

export function knobDetail(knob: Pick<Knob, "name" | "description">): string {
  if (LABELS[knob.name]) return capital(translate(knob.description));
  const area = knob.name.includes(".") ? AREAS[knob.name.split(".")[0]] : undefined;
  return area ?? "";
}

const DECIMAL = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

export function knobValue(knob: Pick<Knob, "name" | "share" | "integer">, value: number | null | undefined): string {
  if (value == null) return "—";
  if (knob.share) return `${DECIMAL.format(value * 100)}%`;
  if (knob.integer) return DECIMAL.format(Math.round(value));
  if (knob.name.endsWith("_hours")) return `${DECIMAL.format(value)} h`;
  if (knob.name.endsWith("_minutes")) return `${DECIMAL.format(value)} min`;
  return DECIMAL.format(value);
}
