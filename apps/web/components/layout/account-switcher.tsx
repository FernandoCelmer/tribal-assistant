"use client";

import { Check, ChevronsUpDown } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useReadOnly } from "./read-only";

type Account = Schemas["AccountOut"];

export function AccountSwitcher({ accounts, current }: { accounts: Account[]; current: Account | null }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const locked = useReadOnly();
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", esc); };
  }, [open]);

  const choose = (id: number) => {
    document.cookie = `tw_account=${id}; path=/; max-age=31536000; samesite=lax`;
    setOpen(false);
    router.refresh();
  };

  if (!current) {
    if (locked) return <div className="flex h-12 items-center rounded-[7px] border border-dashed border-border px-3 text-sm text-secondary">Nenhuma conta cadastrada</div>;
    return <a href="/accounts" className="flex h-12 items-center rounded-[7px] border border-dashed border-border px-3 text-sm text-secondary hover:text-foreground">Cadastrar uma conta</a>;
  }

  return (
    <div ref={box} className="relative">
      <button type="button" aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen((v) => !v)} className="flex h-12 w-full items-center gap-3 rounded-[7px] border border-border bg-surface px-3 text-left transition-colors hover:border-border-hover">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-md border border-border font-mono text-[11px] uppercase text-secondary">{current.server.replace(/[^0-9]/g, "").slice(-3) || current.server.slice(0, 3)}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">{current.name}</span>
          <span className="block truncate font-mono text-[11px] text-muted-foreground">{current.server}</span>
        </span>
        <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
      </button>
      {open && (
        <ul role="listbox" className="select-in absolute inset-x-0 top-[calc(100%+6px)] z-50 overflow-hidden rounded-[7px] border border-border bg-surface py-1">
          {accounts.map((a) => (
            <li key={a.id}>
              <button type="button" role="option" aria-selected={a.id === current.id} onClick={() => choose(a.id)} className={cn("flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-surface-hover", a.id === current.id ? "text-foreground" : "text-secondary")}>
                <span className="min-w-0 flex-1 truncate">{a.name}{!a.enabled && <span className="ml-1 text-muted-foreground">(pausada)</span>}</span>
                <span className="font-mono text-[11px] text-muted-foreground">{a.server}</span>
                {a.id === current.id && <Check className="size-4" strokeWidth={1.75} />}
              </button>
            </li>
          ))}
          {!locked && <li className="border-t border-border-subtle">
            <a href="/accounts" className="block px-3 py-2 text-[13px] text-secondary hover:bg-surface-hover hover:text-foreground">Gerenciar contas</a>
          </li>}
        </ul>
      )}
    </div>
  );
}
