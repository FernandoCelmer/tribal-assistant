"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/logo";
import type { Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";
import { AccountSwitcher } from "./account-switcher";
import { navGroups, active } from "./nav";
import { ReadOnlyBadge, useReadOnly } from "./read-only";

const link = "mx-3 my-0.5 flex h-10 min-h-10 items-center gap-3 rounded-[7px] border px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground";
const on = "border-border bg-surface-selected text-foreground";
const off = "border-transparent text-secondary hover:bg-surface-hover hover:text-foreground";

type Props = { versions: { web: string; api: string }; accounts: Schemas["AccountOut"][]; current: Schemas["AccountOut"] | null };

export function Sidebar({ versions, accounts, current }: Props) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const groups = navGroups(useReadOnly());

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const panel = (
    <div className="flex h-full flex-col">
      <div className="flex h-[66px] items-center gap-2.5 border-b border-border px-5">
        <Logo className="size-5 text-gold" />
        <span className="flex min-w-0 flex-col items-start gap-0.5">
          <span className="text-[15px] font-semibold leading-5">Tribal Assistant</span>
          <ReadOnlyBadge className="h-5 px-1.5 text-[10px]" />
        </span>
        <button type="button" aria-label="Fechar menu" onClick={() => setOpen(false)} className="ml-auto flex size-11 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground md:hidden"><X className="size-4" /></button>
      </div>
      <div className="border-b border-border px-3 py-3">
        <AccountSwitcher accounts={accounts} current={current} />
      </div>
      <nav aria-label="Principal" className="flex-1 overflow-y-auto py-2">
        {groups.map((group) => (
          <div key={group.label} className="mb-2">
            <div className="mx-5 mb-1 mt-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{group.label}</div>
            {group.items.map((item) => {
              const Icon = item.icon;
              const isOn = active(pathname, item);
              return (
                <Link key={item.href} href={item.href} aria-current={isOn ? "page" : undefined} className={cn(link, isOn ? on : off)}>
                  <Icon className="size-[18px]" strokeWidth={1.75} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="flex flex-wrap gap-x-3 border-t border-border-subtle px-5 py-2.5 font-mono text-[11px] text-muted-foreground">
        <span>web {versions.web}</span>
        <span>api {versions.api}</span>
        <a href="/docs" target="_blank" rel="noopener" className="ml-auto hover:text-foreground">API</a>
      </div>
    </div>
  );

  return (
    <>
      <aside className="fixed inset-y-0 left-0 hidden w-[280px] border-r border-border bg-sidebar md:block xl:w-[304px]">{panel}</aside>

      <header className="sticky top-0 z-30 flex h-14 items-center gap-2.5 border-b border-border bg-sidebar pl-4 pr-1.5 md:hidden">
        <Logo className="size-5 text-gold" />
        <span className="truncate text-[15px] font-semibold">Tribal Assistant</span>
        <ReadOnlyBadge className="ml-1" />
        <button type="button" aria-label="Abrir menu" aria-expanded={open} aria-controls="mobile-nav" onClick={() => setOpen(true)} className="ml-auto flex size-11 items-center justify-center rounded-md text-secondary hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground">
          <Menu className="size-5" />
        </button>
      </header>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden" onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
          <div className="absolute inset-0 bg-background/80" />
          <aside id="mobile-nav" role="dialog" aria-modal="true" aria-label="Menu" className="absolute inset-y-0 right-0 w-[300px] max-w-[88vw] border-l border-border bg-sidebar">{panel}</aside>
        </div>
      )}
    </>
  );
}
