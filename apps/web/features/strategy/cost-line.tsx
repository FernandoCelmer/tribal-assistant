import { Users } from "lucide-react";
import { ResourceValue } from "@/components/game/resource";
import { num } from "@/lib/format";
import type { Resource } from "@/lib/game";
import { cn } from "@/lib/utils";
import type { Cost } from "./types";

const KEYS: [keyof Cost, Resource | "pop"][] = [
  ["wood", "wood"],
  ["clay", "clay"],
  ["stone", "clay"],
  ["iron", "iron"],
  ["pop", "pop"],
];

export function CostLine({ cost, empty = "sem custo", all, className }: { cost?: Cost | null; empty?: string; all?: boolean; className?: string }) {
  const parts = KEYS.filter(([key]) => (all && key !== "stone" && key !== "pop") || (cost?.[key] ?? 0) > 0);
  if (!parts.length) return <span className={cn("text-[13px] text-muted-foreground", className)}>{empty}</span>;
  return (
    <span className={cn("inline-flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]", className)}>
      {parts.map(([key, kind]) =>
        kind === "pop" ? (
          <span key={key} className="inline-flex items-center gap-1.5 tabular-nums" title="População">
            <Users className="size-3.5 text-muted-foreground" strokeWidth={1.75} />
            {num(cost?.pop)}
          </span>
        ) : (
          <ResourceValue key={key} kind={kind} value={cost?.[key] ?? 0} />
        ),
      )}
    </span>
  );
}
