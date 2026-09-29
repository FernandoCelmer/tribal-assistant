import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";

export function Loader({ label = "Carregando", className, size = "md" }: { label?: string; className?: string; size?: "sm" | "md" }) {
  const box = size === "sm" ? "size-10" : "size-16";
  const mark = size === "sm" ? "size-4" : "size-7";
  return (
    <div role="status" aria-live="polite" className={cn("flex flex-col items-center justify-center gap-4", className)}>
      <div className={cn("relative flex items-center justify-center", box)}>
        <span aria-hidden className="loader-ring absolute inset-0 rounded-full border border-border border-t-foreground" />
        <span aria-hidden className="absolute inset-[6px] rounded-full border border-border-subtle" />
        <Logo className={cn("loader-mark text-foreground", mark)} />
      </div>
      <div className="flex items-center gap-1.5 text-[13px] text-secondary">
        <span>{label}</span>
        <span aria-hidden className="flex gap-0.5">
          {[0, 1, 2].map((i) => <span key={i} className="loader-dot size-1 rounded-full bg-secondary" style={{ animationDelay: `${i * 160}ms` }} />)}
        </span>
      </div>
    </div>
  );
}

export function PageLoader({ label }: { label?: string }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Loader label={label} />
    </div>
  );
}
