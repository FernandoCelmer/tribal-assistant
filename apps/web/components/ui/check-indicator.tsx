import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function CheckIndicator({ selected, className }: { selected: boolean; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors",
        selected ? "border-foreground bg-foreground text-primary-foreground" : "border-border",
        className,
      )}
    >
      {selected && <Check className="size-3" strokeWidth={3} />}
    </span>
  );
}
