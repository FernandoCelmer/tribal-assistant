import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Props = HTMLAttributes<HTMLSpanElement> & { tone?: "neutral" | "ok" | "bad" | "inverse" | "success" | "warning" | "danger" };

export function Badge({ className, tone = "neutral", ...props }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border",
        tone === "neutral" && "border-border text-secondary",
        tone === "ok" && "border-foreground/60 text-foreground",
        tone === "bad" && "border-foreground bg-foreground text-primary-foreground",
        tone === "inverse" && "border-foreground bg-foreground text-primary-foreground",
        tone === "success" && "border-status-ok/30 bg-status-ok/10 text-status-ok",
        tone === "warning" && "border-status-warn/30 bg-status-warn/10 text-status-warn",
        tone === "danger" && "border-status-bad/30 bg-status-bad/10 text-status-bad",
        className,
      )}
      {...props}
    />
  );
}
