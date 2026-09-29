import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Stat({ label, value, hint, icon: Icon, tone, className }: { label: string; value: ReactNode; hint?: ReactNode; icon?: LucideIcon; tone?: "ok" | "bad" | "warn"; className?: string }) {
  return (
    <div className={cn("flex min-h-[100px] flex-col rounded-lg border border-border bg-surface p-4 sm:min-h-[112px] sm:p-5", className)}>
      <div className="flex items-center justify-between gap-3">
        <span className="truncate text-[13px] text-secondary">{label}</span>
        {Icon && <Icon className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} aria-hidden />}
      </div>
      <div className={cn("mt-3 text-[28px] font-semibold leading-none tabular-nums sm:text-[32px]", tone === "bad" && "text-status-bad", tone === "ok" && "text-status-ok", tone === "warn" && "text-status-warn")}>{value}</div>
      {hint && <div className="mt-2 truncate text-[13px] text-secondary">{hint}</div>}
    </div>
  );
}
