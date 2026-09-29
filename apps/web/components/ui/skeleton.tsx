import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/page";
import { Loader } from "@/components/ui/loader";
import { cn } from "@/lib/utils";

export function Block({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-lg bg-surface", className)} />;
}

export function SkeletonStage({ children, label, className }: { children: ReactNode; label?: string; className?: string }) {
  return (
    <div aria-busy className={cn("relative", className)}>
      <div className="opacity-70">{children}</div>
      <div className="pointer-events-none absolute inset-0 flex items-start justify-center pt-[18vh]">
        <div className="rounded-xl border border-border bg-background/90 px-8 py-6 backdrop-blur-sm"><Loader label={label} /></div>
      </div>
    </div>
  );
}

export function PanelSkeleton({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div aria-hidden className={cn("overflow-hidden rounded-lg border border-border bg-surface", className)}>
      <div className="flex h-12 items-center border-b border-border px-4"><div className="h-4 w-32 animate-pulse rounded bg-surface-hover" /></div>
      <div className="space-y-3 p-4">{Array.from({ length: rows }).map((_, i) => <div key={i} className="h-4 animate-pulse rounded bg-surface-hover" style={{ width: `${88 - (i % 3) * 18}%` }} />)}</div>
    </div>
  );
}

export function TableSkeleton({ rows = 6, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <div aria-hidden className="overflow-hidden rounded-lg border border-border bg-surface">
      <div className="flex gap-6 border-b border-border px-4 py-3">{Array.from({ length: columns }).map((_, i) => <div key={i} className="h-3 flex-1 animate-pulse rounded bg-surface-hover" />)}</div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-6 border-b border-border-subtle px-4 py-3.5 last:border-0">{Array.from({ length: columns }).map((_, c) => <div key={c} className="h-4 flex-1 animate-pulse rounded bg-surface-hover" style={{ opacity: 1 - c * 0.12 }} />)}</div>
      ))}
    </div>
  );
}

export function CardGridSkeleton({ count = 6, height = "h-[180px]", cols = "md:grid-cols-2 xl:grid-cols-3" }: { count?: number; height?: string; cols?: string }) {
  return (
    <div aria-hidden className={cn("grid grid-cols-1 gap-4", cols)}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={cn("flex flex-col rounded-lg border border-border bg-surface px-6 py-[22px]", height)}>
          <div className="size-12 animate-pulse rounded-lg bg-surface-hover" />
          <div className="mt-4 h-5 w-2/3 animate-pulse rounded bg-surface-hover" />
          <div className="mt-2 h-3.5 w-1/3 animate-pulse rounded bg-surface-hover" />
          <div className="mt-auto h-4 w-1/2 animate-pulse rounded bg-surface-hover" />
        </div>
      ))}
    </div>
  );
}

export function PageSkeleton({ title, description, variant = "panels", label }: { title?: string; description?: string; variant?: "panels" | "table" | "cards" | "form"; label?: string }) {
  return (
    <>
      {title ? <PageHeader title={title} description={description} /> : (
        <div aria-hidden className="mb-6"><Block className="h-8 w-56" /><Block className="mt-2 h-4 w-80" /></div>
      )}
      <SkeletonStage label={label}>
        {variant === "table" && <TableSkeleton />}
        {variant === "cards" && <CardGridSkeleton />}
        {variant === "form" && <div className="mx-auto max-w-2xl space-y-4"><PanelSkeleton rows={5} /><PanelSkeleton rows={3} /></div>}
        {variant === "panels" && (
          <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
            <div className="space-y-4"><PanelSkeleton rows={5} /><PanelSkeleton rows={4} /></div>
            <div className="space-y-4"><PanelSkeleton rows={4} /><PanelSkeleton rows={3} /></div>
          </div>
        )}
      </SkeletonStage>
    </>
  );
}
