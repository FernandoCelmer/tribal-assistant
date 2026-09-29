"use client";

import type { LucideIcon } from "lucide-react";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Button } from "./button";
import { Select } from "./select";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";
import { Pager, usePaged } from "./pagination";

export const PER_PAGE = [10, 25, 50, 100] as const;

export const TABLE = { toolbar: 56, header: 40, row: 52, footer: 56, rows: 10, padding: 16, gap: 16, radius: 10 } as const;

export type Hide = "sm" | "md" | "lg" | "xl";
export type Column<T> = { key: string; label: string; width: number; align?: "left" | "right"; hide?: Hide; render: (row: T, index: number) => ReactNode };

const HIDE: Record<Hide, string> = { sm: "hidden sm:table-cell", md: "hidden md:table-cell", lg: "hidden lg:table-cell", xl: "hidden xl:table-cell" };

export type PageState = { total: number; page: number; per: number };

type Props<T> = {
  title: string;
  rows: T[];
  paging?: PageState;
  rowKey: (row: T) => string;
  columns: Column<T>[];
  noun: [string, string];
  meta?: ReactNode;
  action?: ReactNode;
  newHref?: string | null;
  newLabel?: string;
  empty: { icon: LucideIcon; title: string; text?: ReactNode };
  pageKey?: string;
  minWidth?: number;
  rowClassName?: (row: T) => string | undefined;
  description?: ReactNode;
};

export function NewLink({ href, label }: { href: string; label: string }) {
  return <Link href={href} className="inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-md border border-border px-3 text-sm font-medium hover:border-border-hover hover:bg-surface-hover"><Plus className="size-3.5" strokeWidth={2} /> {label}</Link>;
}

export function Cell({ children, className, mono, muted, title }: { children: ReactNode; className?: string; mono?: boolean; muted?: boolean; title?: string }) {
  return <span title={title} suppressHydrationWarning className={cn("block min-w-0 truncate", mono && "font-mono text-[13px]", muted && "text-secondary", className)}>{children}</span>;
}

export function Inline({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("flex min-w-0 items-center gap-2 whitespace-nowrap", className)}>{children}</span>;
}

function usePageNav(key = "") {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const pageKey = key ? `${key}_page` : "page";
  const perKey = key ? `${key}_per` : "per";
  return (next: { page?: number; per?: number }) => {
    const q = new URLSearchParams(params.toString());
    if (next.per !== undefined) { q.set(perKey, String(next.per)); q.set(pageKey, "1"); }
    if (next.page !== undefined) q.set(pageKey, String(next.page));
    router.replace(`${pathname}?${q.toString()}`, { scroll: false });
  };
}

export function DataTable<T>({ title, rows, paging: paged, rowKey, columns, noun, meta, action, newHref, newLabel = "New", empty, pageKey, minWidth = 720, rowClassName, description }: Props<T>) {
  const nav = usePageNav(pageKey);
  const local = usePaged(rows);
  const paging = paged ?? { total: local.total, page: local.page, per: local.per };
  const shown = paged ? rows : local.rows;
  const pages = Math.max(1, Math.ceil(paging.total / Math.max(1, paging.per)));
  const offset = (paging.page - 1) * paging.per;
  const slots = paged || local.pages > 1 ? Math.max(0, paging.per - shown.length) : 0;
  const from = paging.total === 0 ? 0 : offset + 1;
  const to = Math.min(paging.total, offset + shown.length);
  const cell = "px-2 first:pl-4 last:pr-4";
  const Icon = empty.icon;

  return (
    <section className="overflow-hidden border border-border bg-surface" style={{ borderRadius: TABLE.radius }}>
      <header className="flex flex-col gap-2 border-b border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:py-0" style={{ minHeight: TABLE.toolbar }}>
        <div className="min-w-0 sm:py-2">
          <div className="flex min-w-0 items-baseline gap-3">
            <h2 className="truncate text-sm font-semibold">{title}</h2>
            <span className="truncate text-[13px] text-secondary">{paging.total} {paging.total === 1 ? noun[0] : noun[1]}{meta && <span className="hidden sm:inline"> · {meta}</span>}</span>
          </div>
          {description && <p className="mt-0.5 truncate text-[13px] text-secondary">{description}</p>}
        </div>
        {(action || newHref) && (
          <div className="flex shrink-0 flex-wrap items-center gap-2 [&>*]:h-9 [&>*]:flex-1 sm:[&>*]:h-8 sm:[&>*]:flex-none">
            {action}
            {newHref && <NewLink href={newHref} label={newLabel} />}
          </div>
        )}
      </header>

      <ul className="divide-y divide-border-subtle md:hidden">
        {paging.total === 0 && (
          <li className="px-4 py-10 text-center">
            <Icon className="mx-auto size-5 text-secondary" strokeWidth={1.5} />
            <div className="mt-3 text-sm font-medium">{empty.title}</div>
            {empty.text && <div className="mx-auto mt-0.5 max-w-md text-[13px] text-secondary">{empty.text}</div>}
          </li>
        )}
        {shown.map((row, i) => {
          const [head, ...rest] = columns;
          const trailing = rest.filter((c) => c.align === "right" && !c.label);
          const fields = rest.filter((c) => !(c.align === "right" && !c.label));
          return (
            <li key={rowKey(row)} className={cn("px-4 py-3", rowClassName?.(row))}>
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1 text-sm">{head.render(row, offset + i)}</div>
                {trailing.length > 0 && <div className="flex shrink-0 items-center gap-1">{trailing.map((c) => <span key={c.key}>{c.render(row, offset + i)}</span>)}</div>}
              </div>
              {fields.length > 0 && (
                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1.5 text-[13px]">
                  {fields.map((c) => (
                    <div key={c.key} className="min-w-0">
                      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{c.label}</dt>
                      <dd className="min-w-0 truncate">{c.render(row, offset + i)}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </li>
          );
        })}
      </ul>

      <div className="hidden overflow-x-auto md:block">
        <table className="w-full table-fixed text-sm" style={{ minWidth }}>
          <colgroup>{columns.map((c) => <col key={c.key} className={c.hide ? HIDE[c.hide].replace("table-cell", "table-column") : undefined} style={{ width: `${c.width}%` }} />)}</colgroup>
          <thead>
            <tr style={{ height: TABLE.header }}>
              {columns.map((c) => <th key={c.key} className={cn(cell, "whitespace-nowrap text-left text-xs font-medium text-muted-foreground", c.align === "right" && "text-right", c.hide && HIDE[c.hide])}>{c.label}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle border-t border-border-subtle">
            {paging.total === 0 && (
              <tr style={{ height: TABLE.row * TABLE.rows }}>
                <td colSpan={columns.length} className="px-4 text-center align-middle">
                  <Icon className="mx-auto size-5 text-secondary" strokeWidth={1.5} />
                  <div className="mt-3 text-sm font-medium">{empty.title}</div>
                  {empty.text && <div className="mx-auto mt-0.5 max-w-md text-[13px] text-secondary">{empty.text}</div>}
                </td>
              </tr>
            )}
            {shown.map((row, i) => (
              <tr key={rowKey(row)} className={cn("align-middle", rowClassName?.(row))} style={{ height: TABLE.row, minHeight: TABLE.row, maxHeight: TABLE.row }}>
                {columns.map((c) => <td key={c.key} className={cn(cell, "overflow-hidden whitespace-nowrap align-middle", c.align === "right" && "text-right", c.hide && HIDE[c.hide])}>{c.render(row, offset + i)}</td>)}
              </tr>
            ))}
            {paging.total > 0 && Array.from({ length: slots }).map((_, i) => (
              <tr key={`slot-${i}`} aria-hidden style={{ height: TABLE.row }}><td colSpan={columns.length} /></tr>
            ))}
          </tbody>
        </table>
      </div>

      {paged && <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-2 text-[13px] text-secondary sm:flex-nowrap sm:gap-4 sm:py-0" style={{ minHeight: TABLE.footer }}>
        <span className="truncate">{from}–{to} de {paging.total} {paging.total === 1 ? noun[0] : noun[1]}</span>
        <div className="flex shrink-0 items-center gap-2">
          <Select size="sm" value={String(paging.per)} onChange={(v) => nav({ per: Number(v) })} aria-label="Itens por página" options={PER_PAGE.map((n) => ({ value: String(n), label: `${n} por página` }))} className="w-32" />
          <Button size="icon" variant="ghost" aria-label="Página anterior" disabled={paging.page <= 1} onClick={() => nav({ page: paging.page - 1 })}><ChevronLeft className="size-4" strokeWidth={1.75} /></Button>
          <span className="tabular-nums">{paging.page} / {pages}</span>
          <Button size="icon" variant="ghost" aria-label="Próxima página" disabled={paging.page >= pages} onClick={() => nav({ page: paging.page + 1 })}><ChevronRight className="size-4" strokeWidth={1.75} /></Button>
        </div>
      </footer>}
      {!paged && <Pager paging={local} noun={noun} />}
    </section>
  );
}
