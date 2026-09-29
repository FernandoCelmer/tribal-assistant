"use client";

import { cn } from "@/lib/utils";

export type Segment<T extends string> = { id: T; label: string; hint?: string };

export function SegmentedControl<T extends string>({ value, options, onChange, label, className }: { value: T; options: Segment<T>[]; onChange: (v: T) => void; label: string; className?: string }) {
  return (
    <div role="radiogroup" aria-label={label} className={cn("grid h-[42px] w-full overflow-hidden rounded-[7px] border border-border", className)} style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
      {options.map((o) => (
        <button key={o.id} type="button" role="radio" aria-checked={value === o.id} onClick={() => onChange(o.id)} className={cn("flex flex-col items-center justify-center px-3 text-sm leading-tight transition-colors focus-visible:outline-none focus-visible:bg-surface-hover", value === o.id ? "bg-surface-selected text-foreground" : "text-secondary hover:text-foreground")}>
          <span>{o.label}</span>
          {o.hint && <span className={cn("font-mono text-[11px]", value === o.id ? "text-secondary" : "text-muted-foreground")}>{o.hint}</span>}
        </button>
      ))}
    </div>
  );
}
