export type Result = "green" | "yellow" | "red" | "blue";

export const RESULTS: Record<Result, { label: string; short: string; dot: string }> = {
  green: { label: "Vitória sem perdas", short: "Vitórias", dot: "bg-status-ok" },
  yellow: { label: "Vitória com perdas", short: "Perdas", dot: "bg-status-warn" },
  red: { label: "Derrota", short: "Derrotas", dot: "bg-status-bad" },
  blue: { label: "Espionagem", short: "Espionagem", dot: "bg-[#60a5fa]" },
};

export function resultOf(value: string | null | undefined): Result | null {
  return value && value in RESULTS ? (value as Result) : null;
}
