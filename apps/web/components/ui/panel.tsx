import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Panel({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={cn("overflow-hidden rounded-lg border border-border bg-surface", className)} {...props} />;
}

export function PanelHeader({ title, description, aside, className }: { title: ReactNode; description?: ReactNode; aside?: ReactNode; className?: string }) {
  return (
    <header className={cn("flex min-h-12 flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-border px-4 py-2", description && "py-3", className)}>
      <div className="min-w-0">
        <h2 className="flex items-center gap-2 text-sm font-semibold">{title}</h2>
        {description && <p className="mt-0.5 text-[13px] text-secondary">{description}</p>}
      </div>
      {aside}
    </header>
  );
}

export function PanelBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-4", className)} {...props} />;
}
