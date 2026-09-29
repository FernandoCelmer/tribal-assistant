"use client";

import { type ReactNode, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

export type MenuItem = { label: string; onSelect: () => void; danger?: boolean; icon?: ReactNode };

const WIDTH = 176;

export function Menu({ trigger, items, align = "end", label }: { trigger: (props: { open: boolean; toggle: () => void; id: string | undefined }) => ReactNode; items: (MenuItem | "separator")[]; align?: "start" | "end"; label: string }) {
  const [open, setOpen] = useState(false);
  const [rect, setRect] = useState<{ top: number; left: number } | null>(null);
  const id = useId();
  const anchor = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLDivElement>(null);

  const place = () => {
    const a = anchor.current?.getBoundingClientRect();
    if (!a) return;
    const height = list.current?.offsetHeight ?? items.length * 36 + 8;
    const up = a.bottom + height + 8 > window.innerHeight && a.top > height + 8;
    const left = align === "end" ? Math.max(8, a.right - WIDTH) : Math.min(a.left, window.innerWidth - WIDTH - 8);
    setRect({ top: up ? a.top - height - 4 : a.bottom + 4, left });
  };

  useLayoutEffect(() => {
    if (open) place();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { const t = e.target as Node; if (!anchor.current?.contains(t) && !list.current?.contains(t)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    const move = () => place();
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", key);
    window.addEventListener("scroll", move, true);
    window.addEventListener("resize", move);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", key); window.removeEventListener("scroll", move, true); window.removeEventListener("resize", move); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <div ref={anchor} className="inline-flex">
      {trigger({ open, toggle: () => setOpen((v) => !v), id: open ? id : undefined })}
      {open && rect && typeof document !== "undefined" && createPortal(
        <div ref={list} id={id} role="menu" aria-label={label} style={{ top: rect.top, left: rect.left, minWidth: WIDTH }} className="fixed z-50 rounded-lg border border-border bg-surface p-1 shadow-[0_8px_24px_rgba(0,0,0,0.4)]">
          {items.map((item, i) =>
            item === "separator" ? (
              <div key={i} role="separator" className="my-1 h-px bg-border-subtle" />
            ) : (
              <button
                key={i}
                type="button"
                role="menuitem"
                onClick={() => { setOpen(false); item.onSelect(); }}
                className={cn("flex w-full items-center gap-2 whitespace-nowrap rounded-md px-2.5 py-2 text-left text-sm hover:bg-surface-hover focus-visible:outline-none focus-visible:bg-surface-hover", item.danger ? "text-foreground" : "text-secondary hover:text-foreground")}
              >
                {item.icon}
                {item.label}
              </button>
            ),
          )}
        </div>,
        document.body,
      )}
    </div>
  );
}
