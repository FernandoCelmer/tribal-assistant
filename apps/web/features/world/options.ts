export type Kind = "barbarian" | "player" | "all";

export const KINDS: { id: Kind; label: string }[] = [
  { id: "barbarian", label: "Bárbaras" },
  { id: "player", label: "Jogadores" },
  { id: "all", label: "Todas" },
];

export const RADII = [5, 10, 15, 20, 30, 50];

export function parseKind(raw: unknown): Kind {
  return KINDS.some((k) => k.id === raw) ? (raw as Kind) : "barbarian";
}

export function parseRadius(raw: unknown): number {
  const value = Number(raw);
  return Number.isInteger(value) && value >= 1 && value <= 100 ? value : 15;
}
