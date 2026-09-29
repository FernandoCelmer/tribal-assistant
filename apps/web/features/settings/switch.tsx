"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Switch({ checked, onChange, label, disabled, busy, className }: { checked: boolean; onChange: (value: boolean) => void; label: string; disabled?: boolean; busy?: boolean; className?: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      aria-busy={busy || undefined}
      disabled={disabled || busy}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-50",
        checked ? "border-foreground bg-foreground" : "border-border bg-surface-hover",
        busy && "animate-pulse",
        className,
      )}
    >
      <span aria-hidden className={cn("size-3.5 rounded-full transition-transform duration-150", checked ? "translate-x-[18px] bg-background" : "translate-x-[2px] bg-secondary")} />
    </button>
  );
}

export function SwitchRow({ title, text, checked, onChange, disabled, aside }: { title: string; text: ReactNode; checked: boolean; onChange: (value: boolean) => void; disabled?: boolean; aside?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-3.5 first:pt-0 last:pb-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2 text-sm font-medium">{title}{aside}</div>
        <p className="mt-0.5 text-[13px] text-secondary">{text}</p>
      </div>
      <Switch checked={checked} onChange={onChange} label={title} disabled={disabled} className="mt-0.5" />
    </div>
  );
}
