const NUMBER = new Intl.NumberFormat("pt-BR");

export function num(value: number | null | undefined): string {
  return value == null ? "—" : NUMBER.format(value);
}

export function utc(value: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`);
}

export function duration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  const s = Math.max(0, Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h) return `${h}h ${String(m).padStart(2, "0")}m`;
  if (m) return `${m}m ${String(s % 60).padStart(2, "0")}s`;
  return `${s}s`;
}

export function relative(value: string | null | undefined, now = Date.now()): string {
  if (!value) return "—";
  const diff = (utc(value).getTime() - now) / 1000;
  return diff >= 0 ? `em ${duration(diff)}` : `há ${duration(-diff)}`;
}

export function when(value: string | null | undefined): string {
  return value ? utc(value).toLocaleString("pt-BR") : "—";
}

export function short(value: string | null | undefined): string {
  return value ? utc(value).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
}

export function percent(value: number | null | undefined): string {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}
