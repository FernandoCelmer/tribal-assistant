import type { Schemas } from "@/lib/api";

type Knob = Schemas["KnobOut"];

const LABELS: Record<string, string> = {
  base_stock_share: "Reserva mínima do estoque",
  filler_wait_hours: "Espera antes de obra encaixe",
  scavenge_share: "Lanceiros na coleta",
};

export function knobLabel(name: string): string {
  if (LABELS[name]) return LABELS[name];
  const text = name.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
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
