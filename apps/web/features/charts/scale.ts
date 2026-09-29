export type Series = { key: string; label: string; tone: string; values: number[]; dashed?: boolean };

export const SHADES = ["text-neutral-100", "text-neutral-400", "text-neutral-600", "text-neutral-300", "text-neutral-500", "text-neutral-200", "text-neutral-700"];

export const RESOURCE_TONES = { wood: "text-wood", clay: "text-clay", iron: "text-iron" } as const;

export const PERIODS = [
  { id: "24", label: "24h" },
  { id: "168", label: "7d" },
  { id: "720", label: "30d" },
] as const;

export type Period = (typeof PERIODS)[number]["id"];

export function period(value: string | undefined, fallback: Period = "24"): Period {
  return PERIODS.some((p) => p.id === value) ? (value as Period) : fallback;
}

export function ticks(max: number, count = 4): number[] {
  if (max <= 0) return [0, 1];
  const raw = max / count;
  const power = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((s) => s >= raw) ?? raw;
  const top = Math.ceil(max / step) * step;
  const out: number[] = [];
  for (let v = 0; v <= top + step / 2; v += step) out.push(Math.round(v * 1000) / 1000);
  return out;
}

const COMPACT = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });

export function compact(value: number): string {
  return COMPACT.format(value);
}

export function hourLabel(date: Date): string {
  return `${String(date.getHours()).padStart(2, "0")}h`;
}

export function dayLabel(date: Date): string {
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export function stamp(date: Date): string {
  return date.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}
