"use client";

import { Eye } from "lucide-react";
import { createContext, useContext, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const ReadOnlyContext = createContext(false);

export function ReadOnlyProvider({ value, children }: { value: boolean; children: ReactNode }) {
  return <ReadOnlyContext.Provider value={value}>{children}</ReadOnlyContext.Provider>;
}

export function useReadOnly(): boolean {
  return useContext(ReadOnlyContext);
}

export function Writable({ children }: { children: ReactNode }) {
  return useReadOnly() ? null : <>{children}</>;
}

export function ReadOnlyBadge({ className }: { className?: string }) {
  if (!useReadOnly()) return null;
  return (
    <span title="O servidor não joga (PLAY=false): o painel só mostra dados" className={cn("inline-flex h-6 shrink-0 items-center gap-1.5 rounded-full border border-border px-2 text-[11px] font-medium text-secondary", className)}>
      <Eye className="size-3" strokeWidth={1.75} aria-hidden />
      somente leitura
    </span>
  );
}
