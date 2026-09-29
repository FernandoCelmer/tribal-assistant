"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Children, createContext, useContext, useState, type ReactNode } from "react";
import { Button } from "./button";
import { Select } from "./select";
import { cn } from "@/lib/utils";

export const PAGE_SIZES = [10, 25, 50, 100] as const;

export type Paging = {
  page: number;
  per: number;
  pages: number;
  total: number;
  from: number;
  to: number;
  offset: number;
  go: (page: number) => void;
  resize: (per: number) => void;
};

export function pageCount(total: number, per: number): number {
  return Math.max(1, Math.ceil(total / Math.max(1, per)));
}

export function usePaging(total: number, initial: number = PAGE_SIZES[0]): Paging {
  const [wanted, setWanted] = useState(1);
  const [per, setPer] = useState(initial);
  const pages = pageCount(total, per);
  const page = Math.min(Math.max(1, wanted), pages);
  const offset = (page - 1) * per;

  return {
    page,
    per,
    pages,
    total,
    offset,
    from: total === 0 ? 0 : offset + 1,
    to: Math.min(total, offset + per),
    go: (next) => setWanted(Math.min(Math.max(1, next), pages)),
    resize: (next) => { setPer(next); setWanted(1); },
  };
}

export function usePaged<T>(items: T[], initial?: number): Paging & { rows: T[] } {
  const paging = usePaging(items.length, initial);
  return { ...paging, rows: items.slice(paging.offset, paging.offset + paging.per) };
}

export function Pager({ paging, noun = ["item", "itens"], className }: { paging: Paging; noun?: [string, string]; className?: string }) {
  if (paging.total <= PAGE_SIZES[0]) return null;

  return (
    <footer className={cn("flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-2 text-[13px] text-secondary sm:flex-nowrap sm:gap-4", className)}>
      <span className="truncate tabular-nums">{paging.from}–{paging.to} de {paging.total} {paging.total === 1 ? noun[0] : noun[1]}</span>
      <div className="flex shrink-0 items-center gap-2">
        <Select size="sm" value={String(paging.per)} onChange={(v) => paging.resize(Number(v))} aria-label="Itens por página" options={PAGE_SIZES.map((n) => ({ value: String(n), label: `${n} por página` }))} className="w-36" />
        <Button size="icon" variant="ghost" aria-label="Página anterior" disabled={paging.page <= 1} onClick={() => paging.go(paging.page - 1)}><ChevronLeft className="size-4" strokeWidth={1.75} /></Button>
        <span className="tabular-nums">{paging.page} / {paging.pages}</span>
        <Button size="icon" variant="ghost" aria-label="Próxima página" disabled={paging.page >= paging.pages} onClick={() => paging.go(paging.page + 1)}><ChevronRight className="size-4" strokeWidth={1.75} /></Button>
      </div>
    </footer>
  );
}

const Scope = createContext<Paging | null>(null);

function useScope(): Paging {
  const paging = useContext(Scope);
  if (!paging) throw new Error("PageSlice e PageFooter precisam de um PageScope");
  return paging;
}

export function PageScope({ total, per, children }: { total: number; per?: number; children: ReactNode }) {
  const paging = usePaging(total, per);
  return <Scope.Provider value={paging}>{children}</Scope.Provider>;
}

export function PageSlice({ children }: { children: ReactNode }) {
  const paging = useScope();
  return <>{Children.toArray(children).slice(paging.offset, paging.offset + paging.per)}</>;
}

export function PageFooter({ noun, className }: { noun?: [string, string]; className?: string }) {
  return <Pager paging={useScope()} noun={noun} className={className} />;
}
