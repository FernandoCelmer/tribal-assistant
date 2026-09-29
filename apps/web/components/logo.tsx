import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" aria-label="Tribal Assistant" className={cn("size-5 shrink-0", className)} fill="currentColor">
      <path d="M1.3 4.6 5 7.8 8 2.5l3 5.3 3.7-3.2-1.5 8.2H2.8zM2.8 13.8h10.4v1.4H2.8z" />
    </svg>
  );
}
