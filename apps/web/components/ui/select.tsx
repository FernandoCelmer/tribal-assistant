"use client";

import { Check, ChevronDown } from "lucide-react";
import { type ReactNode, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

export type SelectOption = { value: string; label: string; hint?: string; disabled?: boolean };

type Props = {
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  mono?: boolean;
  size?: "sm" | "md" | "lg";
  icon?: ReactNode;
  className?: string;
  autoFocus?: boolean;
  "aria-label"?: string;
};

const HEIGHTS = { sm: "h-8 text-[13px]", md: "h-9 text-[13px]", lg: "h-10 text-sm" };

export function Select({ value, options, onChange, placeholder = "Select…", disabled, mono, size = "md", icon, className, autoFocus, "aria-label": ariaLabel }: Props) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [rect, setRect] = useState<{ top: number; left: number; width: number; up: boolean } | null>(null);
  const button = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const id = useId();
  const selected = options.find((o) => o.value === value) ?? null;

  const place = () => {
    const b = button.current?.getBoundingClientRect();
    if (!b) return;
    const height = Math.min(320, options.length * 36 + 8);
    const up = b.bottom + height + 8 > window.innerHeight && b.top > height + 8;
    setRect({ top: up ? b.top - height - 4 : b.bottom + 4, left: b.left, width: b.width, up });
  };

  useLayoutEffect(() => {
    if (!open) return;
    place();
    const i = Math.max(0, options.findIndex((o) => o.value === value));
    setActive(i);
    const onScroll = () => place();
    window.addEventListener("resize", onScroll);
    window.addEventListener("scroll", onScroll, true);
    return () => { window.removeEventListener("resize", onScroll); window.removeEventListener("scroll", onScroll, true); };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!button.current?.contains(e.target as Node) && !list.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    list.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [open, active]);

  const pick = (o: SelectOption) => { if (o.disabled) return; onChange(o.value); setOpen(false); button.current?.focus(); };

  const move = (delta: number) => {
    let i = active;
    for (let n = 0; n < options.length; n++) {
      i = (i + delta + options.length) % options.length;
      if (!options[i].disabled) break;
    }
    setActive(i);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (disabled) return;
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) { e.preventDefault(); setOpen(true); }
      return;
    }
    if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(options.length - 1); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (options[active]) pick(options[active]); }
    else if (e.key === "Escape" || e.key === "Tab") { setOpen(false); }
  };

  return (
    <>
      <button
        ref={button}
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        aria-label={ariaLabel}
        disabled={disabled}
        autoFocus={autoFocus}
        onClick={() => !disabled && setOpen((v) => !v)}
        onKeyDown={onKey}
        className={cn(
          "flex w-full items-center gap-2 rounded-md border border-border bg-background pl-3 pr-2.5 text-left text-foreground transition-colors",
          "hover:border-border-hover focus-visible:outline-none focus-visible:border-foreground focus-visible:ring-1 focus-visible:ring-foreground",
          "disabled:cursor-not-allowed disabled:opacity-50",
          open && "border-foreground",
          HEIGHTS[size],
          className,
        )}
      >
        {icon && <span className="shrink-0 text-secondary">{icon}</span>}
        <span className={cn("min-w-0 flex-1 truncate", mono && "font-mono", !selected && "text-muted-foreground")}>{selected ? selected.label : placeholder}</span>
        <ChevronDown className={cn("size-4 shrink-0 text-secondary transition-transform duration-150", open && "rotate-180")} strokeWidth={1.75} />
      </button>
      {open && rect && createPortal(
        <ul
          ref={list}
          id={id}
          role="listbox"
          aria-activedescendant={`${id}-${active}`}
          style={{ top: rect.top, left: rect.left, width: rect.width }}
          className={cn("fixed z-50 max-h-80 overflow-auto rounded-lg border border-border bg-surface p-1 shadow-[0_12px_32px_rgba(0,0,0,0.55)]", rect.up ? "origin-bottom" : "origin-top", "select-in")}
        >
          {options.length === 0 && <li className="px-2.5 py-2 text-[13px] text-muted-foreground">No options</li>}
          {options.map((o, i) => (
            <li
              key={o.value}
              id={`${id}-${i}`}
              data-index={i}
              role="option"
              aria-selected={o.value === value}
              aria-disabled={o.disabled}
              onMouseEnter={() => !o.disabled && setActive(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(o)}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-[13px]",
                i === active && !o.disabled ? "bg-surface-hover text-foreground" : "text-secondary",
                o.disabled && "cursor-not-allowed opacity-50",
                mono && "font-mono",
              )}
            >
              <span className="min-w-0 flex-1 truncate">{o.label}{o.hint && <span className="ml-2 font-sans text-xs text-muted-foreground">{o.hint}</span>}</span>
              {o.value === value && <Check className="size-3.5 shrink-0" strokeWidth={2.5} />}
            </li>
          ))}
        </ul>,
        document.body,
      )}
    </>
  );
}
