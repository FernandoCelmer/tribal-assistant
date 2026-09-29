import { BUILDINGS, UNITS, buildingIcon, unitIcon } from "@/lib/game";
import { cn } from "@/lib/utils";

export function BuildingIcon({ name, level = 1, className }: { name: string; level?: number; className?: string }) {
  return <img src={buildingIcon(name, level)} alt={BUILDINGS[name] ?? name} title={BUILDINGS[name] ?? name} className={cn("size-8 shrink-0 object-contain", className)} />;
}

export function UnitIcon({ name, className }: { name: string; className?: string }) {
  return <img src={unitIcon(name)} alt={UNITS[name] ?? name} title={UNITS[name] ?? name} className={cn("size-[18px] shrink-0 object-contain", className)} />;
}

export function Coords({ value, className }: { value: string; className?: string }) {
  return <span className={cn("font-mono text-[13px] text-secondary", className)}>{value}</span>;
}
