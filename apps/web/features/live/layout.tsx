"use client";

import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";

export type Box = { x: number; y: number; w: number; h: number };
export type CardId = "head" | "graph" | "steps" | "results" | "village";
export type Layout = Record<CardId, Box>;

export const STAGE = { w: 1280, h: 720 };
const GRID = 4;
const MIN = { w: 120, h: 40 };
const STORE = "live-layout-v1";
const PARAM = "layout";

export const DEFAULT_LAYOUT: Layout = {
  head: { x: 12, y: 12, w: 1256, h: 48 },
  graph: { x: 12, y: 72, w: 916, h: 400 },
  steps: { x: 12, y: 484, w: 604, h: 224 },
  results: { x: 628, y: 484, w: 300, h: 224 },
  village: { x: 940, y: 72, w: 328, h: 636 },
};

function snap(value: number): number {
  return Math.round(value / GRID) * GRID;
}

function fit(box: Box): Box {
  const w = Math.min(STAGE.w, Math.max(MIN.w, snap(box.w)));
  const h = Math.min(STAGE.h, Math.max(MIN.h, snap(box.h)));
  return { w, h, x: Math.min(STAGE.w - w, Math.max(0, snap(box.x))), y: Math.min(STAGE.h - h, Math.max(0, snap(box.y))) };
}

function valid(value: unknown): value is Layout {
  if (!value || typeof value !== "object") return false;
  return (Object.keys(DEFAULT_LAYOUT) as CardId[]).every((id) => {
    const box = (value as Record<string, Box>)[id];
    return box && ["x", "y", "w", "h"].every((k) => Number.isFinite((box as Record<string, number>)[k]));
  });
}

function encode(layout: Layout): string {
  return btoa(JSON.stringify(layout)).replace(/=+$/, "");
}

function decode(text: string | null): Layout | null {
  if (!text) return null;
  try {
    const parsed: unknown = JSON.parse(atob(text));
    return valid(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function stored(): Layout | null {
  try {
    return decode(window.localStorage.getItem(STORE));
  } catch {
    return null;
  }
}

function keep(layout: Layout): void {
  try {
    window.localStorage.setItem(STORE, encode(layout));
  } catch {
    return;
  }
}

export function useLayout(fromUrl: string | null) {
  const [layout, setLayout] = useState<Layout>(DEFAULT_LAYOUT);

  useEffect(() => {
    setLayout(decode(fromUrl) ?? stored() ?? DEFAULT_LAYOUT);
  }, [fromUrl]);

  const move = useCallback((id: CardId, box: Box) => {
    setLayout((current) => {
      const next = { ...current, [id]: fit(box) };
      keep(next);
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    keep(DEFAULT_LAYOUT);
    setLayout(DEFAULT_LAYOUT);
  }, []);

  const link = useCallback(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete("edit");
    url.searchParams.set(PARAM, encode(layout));
    return url.toString();
  }, [layout]);

  return { layout, move, reset, link };
}

export function useEditing(initial: boolean): [boolean, (value: boolean) => void] {
  const [editing, setEditing] = useState(initial);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "e" && !event.metaKey && !event.ctrlKey && !event.altKey) setEditing((value) => !value);
      if (event.key === "Escape") setEditing(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return [editing, setEditing];
}

type Drag = { mode: "move" | "resize"; startX: number; startY: number; box: Box };

let front = 1;

export function Card({ id, box, editing, scale, onChange, children }: { id: CardId; box: Box; editing: boolean; scale: number; onChange: (id: CardId, box: Box) => void; children: ReactNode }) {
  const drag = useRef<Drag | null>(null);
  const [z, setZ] = useState(0);

  const start = (mode: Drag["mode"]) => (event: ReactPointerEvent<HTMLElement>) => {
    if (!editing) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { mode, startX: event.clientX, startY: event.clientY, box };
    front += 1;
    setZ(front);
  };

  const moveTo = (event: ReactPointerEvent<HTMLElement>) => {
    const current = drag.current;
    if (!current) return;
    const dx = (event.clientX - current.startX) / scale;
    const dy = (event.clientY - current.startY) / scale;
    const b = current.box;
    onChange(id, current.mode === "move" ? { ...b, x: b.x + dx, y: b.y + dy } : { ...b, w: b.w + dx, h: b.h + dy });
  };

  const stop = () => {
    drag.current = null;
  };

  return (
    <div
      className="live-card"
      data-edit={editing || undefined}
      style={{ left: box.x, top: box.y, width: box.w, height: box.h, zIndex: z }}
      onPointerDown={start("move")}
      onPointerMove={moveTo}
      onPointerUp={stop}
      onPointerCancel={stop}
    >
      {children}
      {editing && <span className="live-grip" onPointerDown={start("resize")} onPointerMove={moveTo} onPointerUp={stop} onPointerCancel={stop} />}
    </div>
  );
}

export function EditBar({ onReset, link, onClose }: { onReset: () => void; link: () => string; onClose: () => void }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link());
      setCopied(true);
      setTimeout(() => setCopied(false), 2_000);
    } catch {
      window.prompt("Link com este layout:", link());
    }
  };

  return (
    <div className="live-editbar">
      <span>Arraste os cards e redimensione pelo canto · E para sair</span>
      <button type="button" onClick={copy}>{copied ? "Link copiado" : "Copiar link para o OBS"}</button>
      <button type="button" onClick={onReset}>Restaurar</button>
      <button type="button" onClick={onClose}>Concluir</button>
    </div>
  );
}

export const LAYOUT_CSS = `
.live-card { position: absolute; }
.live-card[data-edit] { outline: 1px dashed var(--live-running); outline-offset: 2px; cursor: move; user-select: none; }
.live-card[data-edit] > * { pointer-events: none; }
.live-card[data-edit] > .live-grip { pointer-events: auto; }
.live-grip { position: absolute; right: -6px; bottom: -6px; width: 14px; height: 14px; border-radius: 3px; background: var(--live-running); cursor: nwse-resize; }
.live-editbar { white-space: nowrap; position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); z-index: 10; display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--live-line); background: var(--live-panel); font-size: 13px; color: var(--live-dim); box-shadow: 0 8px 24px rgba(0,0,0,.4); }
.live-editbar button { border: 1px solid var(--live-line); background: var(--live-bg); color: var(--live-text); border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
.live-editbar button:hover { border-color: var(--live-running); }
`;
