import { RESOURCES, type Resource } from "@/lib/game";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";

export function ResourceIcon({ kind, className }: { kind: Resource; className?: string }) {
  return <img src={RESOURCES[kind].icon} alt={RESOURCES[kind].label} title={RESOURCES[kind].label} className={cn("size-4 shrink-0", className)} />;
}

export function ResourceValue({ kind, value, className }: { kind: Resource; value: number | null | undefined; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 tabular-nums", className)}>
      <ResourceIcon kind={kind} />
      {num(value)}
    </span>
  );
}

export function Cost({ wood, clay, iron, className }: { wood?: number | null; clay?: number | null; iron?: number | null; className?: string }) {
  return (
    <span className={cn("inline-flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-secondary", className)}>
      <ResourceValue kind="wood" value={wood} />
      <ResourceValue kind="clay" value={clay} />
      <ResourceValue kind="iron" value={iron} />
    </span>
  );
}

export function Meter({ kind, value, max }: { kind: Resource; value: number; max: number }) {
  const ratio = max ? Math.min(1, value / max) : 0;
  const bar = { wood: "bg-wood", clay: "bg-clay", iron: "bg-iron" }[kind];
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-hover" role="meter" aria-valuenow={value} aria-valuemax={max} aria-label={RESOURCES[kind].label}>
      <div className={cn("h-full rounded-full", bar, ratio > 0.9 && "bg-status-bad")} style={{ width: `${ratio * 100}%` }} />
    </div>
  );
}
