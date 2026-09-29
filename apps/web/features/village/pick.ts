export function pickVillage<T extends { id: number }>(villages: T[], raw: string | string[] | undefined): T | null {
  const id = Number(Array.isArray(raw) ? raw[0] : raw);
  return villages.find((v) => v.id === id) ?? villages[0] ?? null;
}
