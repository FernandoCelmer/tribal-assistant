import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function EmptyState({ icon: Icon, title, text, action, className }: { icon: LucideIcon; title: string; text?: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col items-center px-4 py-10 text-center", className)}>
      <Icon className="size-5 text-secondary" strokeWidth={1.5} />
      <div className="mt-3 text-sm font-medium">{title}</div>
      {text && <div className="mt-0.5 max-w-md text-[13px] text-secondary">{text}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
