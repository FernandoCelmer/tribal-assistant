"use client";

import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";

export const STAGE = { w: 1920, h: 1080 };
const GRID = 4;
const MIN = { w: 160, h: 48 };
const STORE = "twitch-board-v1";
const PARAM = "board";
const ROTATE = 12_000;
const LOOSE = { x: 24, y: 92, w: 1276, tile: { w: 304, h: 176 } };
export const FIXED = new Set(["header", "game"]);

export type Frame = { id: string; x: number; y: number; w: number; h: number; cards: string[] };

export const SLIDES = ["session", "thinking", "learning", "builds", "map", "raid", "quests", "production", "social", "protection"];

export const DEFAULT_BOARD: Frame[] = [
  { id: "header", x: 12, y: 12, w: 1896, h: 56, cards: ["header"] },
  { id: "game", x: 12, y: 80, w: 1300, h: 610, cards: ["game"] },
  { id: "village", x: 1324, y: 80, w: 584, h: 162, cards: ["village"] },
  { id: "decision", x: 1324, y: 254, w: 584, h: 142, cards: ["decision"] },
  { id: "moves", x: 1324, y: 408, w: 584, h: 136, cards: ["moves"] },
  { id: "highlights", x: 1324, y: 556, w: 584, h: 134, cards: SLIDES },
  { id: "flow", x: 12, y: 702, w: 1452, h: 366, cards: ["flow"] },
  { id: "activity", x: 1476, y: 702, w: 432, h: 366, cards: ["activity"] },
];

function snap(value: number): number {
  return Math.round(value / GRID) * GRID;
}

function fit(frame: Frame): Frame {
  const w = Math.min(STAGE.w, Math.max(MIN.w, snap(frame.w)));
  const h = Math.min(STAGE.h, Math.max(MIN.h, snap(frame.h)));
  return { ...frame, w, h, x: Math.min(STAGE.w - w, Math.max(0, snap(frame.x))), y: Math.min(STAGE.h - h, Math.max(0, snap(frame.y))) };
}

function valid(value: unknown): value is Frame[] {
  return Array.isArray(value) && value.every((f) => f && typeof f.id === "string" && Array.isArray(f.cards) && ["x", "y", "w", "h"].every((k) => Number.isFinite(f[k])));
}

function encode(board: Frame[]): string {
  return btoa(unescape(encodeURIComponent(JSON.stringify(board)))).replace(/=+$/, "");
}

function decode(text: string | null): Frame[] | null {
  if (!text) return null;
  try {
    const parsed: unknown = JSON.parse(decodeURIComponent(escape(atob(text))));
    return valid(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function stored(): Frame[] | null {
  try {
    return decode(window.localStorage.getItem(STORE));
  } catch {
    return null;
  }
}

function keep(board: Frame[]): void {
  try {
    window.localStorage.setItem(STORE, encode(board));
  } catch {
    return;
  }
}

export function useBoard(fromUrl: string | null) {
  const [board, setBoard] = useState<Frame[]>(DEFAULT_BOARD);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    setBoard(decode(fromUrl) ?? stored() ?? DEFAULT_BOARD);
  }, [fromUrl]);

  const commit = useCallback((change: (current: Frame[]) => Frame[]) => {
    setBoard((current) => {
      const next = change(current).map(fit);
      keep(next);
      return next;
    });
  }, []);

  const select = useCallback((id: string, add: boolean) => {
    setSelected((current) => (add ? (current.includes(id) ? current.filter((s) => s !== id) : [...current, id]) : current.includes(id) ? current : [id]));
    setBoard((current) => {
      const picked = current.find((f) => f.id === id);
      return picked ? [...current.filter((f) => f.id !== id), picked] : current;
    });
  }, []);

  const moveBy = useCallback(
    (ids: string[], dx: number, dy: number, origin: Frame[]) => {
      commit(() => origin.map((f) => (ids.includes(f.id) ? { ...f, x: f.x + dx, y: f.y + dy } : f)));
    },
    [commit],
  );

  const resize = useCallback(
    (id: string, w: number, h: number) => {
      commit((current) => current.map((f) => (f.id === id ? { ...f, w, h } : f)));
    },
    [commit],
  );

  const group = useCallback(() => {
    commit((current) => {
      const picked = selected.map((id) => current.find((f) => f.id === id)).filter((f): f is Frame => !!f && !f.cards.some((c) => FIXED.has(c)));
      if (picked.length < 2) return current;
      const [first] = picked;
      const merged: Frame = { ...first, id: `group-${Date.now()}`, cards: picked.flatMap((f) => f.cards) };
      return [...current.filter((f) => !picked.includes(f)), merged];
    });
    setSelected([]);
  }, [commit, selected]);

  const ungroup = useCallback(() => {
    commit((current) => {
      const split = current.filter((f) => selected.includes(f.id) && f.cards.length > 1);
      const cards = split.flatMap((f) => f.cards);
      const columns = Math.max(1, Math.floor((LOOSE.w + GRID * 3) / (LOOSE.tile.w + GRID * 3)));
      const loose = cards.map((card, i) => ({
        id: card,
        cards: [card],
        x: LOOSE.x + (i % columns) * (LOOSE.tile.w + GRID * 3),
        y: LOOSE.y + Math.floor(i / columns) * (LOOSE.tile.h + GRID * 3),
        w: LOOSE.tile.w,
        h: LOOSE.tile.h,
      }));
      return [...current.filter((f) => !split.includes(f)), ...loose];
    });
    setSelected([]);
  }, [commit, selected]);

  const arrange = useCallback(
    (how: "left" | "top" | "horizontal" | "vertical" | "size") => {
      commit((current) => {
        const picked = current.filter((f) => selected.includes(f.id));
        if (picked.length < 2) return current;
        const lead = current.find((f) => f.id === selected[0]) ?? picked[0];
        const change = new Map<string, Partial<Frame>>();
        if (how === "left") picked.forEach((f) => change.set(f.id, { x: lead.x }));
        if (how === "top") picked.forEach((f) => change.set(f.id, { y: lead.y }));
        if (how === "size") picked.forEach((f) => change.set(f.id, { w: lead.w, h: lead.h }));
        if (how === "horizontal" || how === "vertical") {
          const axis = how === "horizontal" ? "x" : "y";
          const size = how === "horizontal" ? "w" : "h";
          const sorted = [...picked].sort((a, b) => a[axis] - b[axis]);
          const start = sorted[0][axis];
          const end = Math.max(...sorted.map((f) => f[axis] + f[size]));
          const room = end - start - sorted.reduce((sum, f) => sum + f[size], 0);
          const space = sorted.length > 1 ? room / (sorted.length - 1) : 0;
          let cursor = start;
          sorted.forEach((f) => {
            change.set(f.id, { [axis]: cursor });
            cursor += f[size] + space;
          });
        }
        return current.map((f) => ({ ...f, ...(change.get(f.id) ?? {}) }));
      });
    },
    [commit, selected],
  );

  const reset = useCallback(() => {
    keep(DEFAULT_BOARD);
    setBoard(DEFAULT_BOARD);
    setSelected([]);
  }, []);

  const link = useCallback(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete("edit");
    url.searchParams.set(PARAM, encode(board));
    return url.toString();
  }, [board]);

  return { board, selected, setSelected, select, moveBy, resize, group, ungroup, arrange, reset, link };
}

export function useEditing(initial: boolean): [boolean, (value: boolean) => void] {
  const [editing, setEditing] = useState(initial);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return;
      if (event.key.toLowerCase() === "e" && !event.metaKey && !event.ctrlKey && !event.altKey) setEditing((value) => !value);
      if (event.key === "Escape") setEditing(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return [editing, setEditing];
}

export function useStage(): number {
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const fitScale = () => setScale(Math.min(window.innerWidth / STAGE.w, window.innerHeight / STAGE.h));
    fitScale();
    window.addEventListener("resize", fitScale);
    return () => window.removeEventListener("resize", fitScale);
  }, []);
  return scale;
}

export function useRotation(count: number): number {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    if (count < 2) return;
    const timer = setInterval(() => setIndex((i) => i + 1), ROTATE);
    return () => clearInterval(timer);
  }, [count]);
  return count ? index % count : 0;
}

type Drag = { mode: "move" | "resize"; x: number; y: number; origin: Frame[]; ids: string[]; w: number; h: number; moved: boolean };

export function Tile({
  frame,
  board,
  editing,
  selected,
  scale,
  onSelect,
  onMove,
  onResize,
  children,
}: {
  frame: Frame;
  board: Frame[];
  editing: boolean;
  selected: string[];
  scale: number;
  onSelect: (id: string, add: boolean) => void;
  onMove: (ids: string[], dx: number, dy: number, origin: Frame[]) => void;
  onResize: (id: string, w: number, h: number) => void;
  children: ReactNode;
}) {
  const drag = useRef<Drag | null>(null);
  const isSelected = selected.includes(frame.id);

  const start = (mode: Drag["mode"]) => (event: ReactPointerEvent<HTMLElement>) => {
    if (!editing) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    if (mode === "move") onSelect(frame.id, event.shiftKey);
    const ids = mode === "move" && isSelected && !event.shiftKey ? selected : [frame.id];
    drag.current = { mode, x: event.clientX, y: event.clientY, origin: board, ids, w: frame.w, h: frame.h, moved: false };
  };

  const moveTo = (event: ReactPointerEvent<HTMLElement>) => {
    const current = drag.current;
    if (!current) return;
    const dx = (event.clientX - current.x) / scale;
    const dy = (event.clientY - current.y) / scale;
    if (!current.moved && Math.hypot(dx, dy) < 3) return;
    current.moved = true;
    if (current.mode === "move") onMove(current.ids, dx, dy, current.origin);
    else onResize(frame.id, current.w + dx, current.h + dy);
  };

  const stop = () => {
    drag.current = null;
  };

  return (
    <div
      className="tw-tile"
      data-edit={editing || undefined}
      data-selected={(editing && isSelected) || undefined}
      style={{ left: frame.x, top: frame.y, width: frame.w, height: frame.h }}
      onPointerDown={start("move")}
      onPointerMove={moveTo}
      onPointerUp={stop}
      onPointerCancel={stop}
    >
      {children}
      {editing && <span className="tw-grip" onPointerDown={start("resize")} onPointerMove={moveTo} onPointerUp={stop} onPointerCancel={stop} />}
    </div>
  );
}

export function Toolbar({
  selected,
  board,
  onGroup,
  onUngroup,
  onArrange,
  onReset,
  link,
  onClose,
}: {
  selected: string[];
  board: Frame[];
  onGroup: () => void;
  onUngroup: () => void;
  onArrange: (how: "left" | "top" | "horizontal" | "vertical" | "size") => void;
  onReset: () => void;
  link: () => string;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const picked = board.filter((f) => selected.includes(f.id));
  const groupable = picked.filter((f) => !f.cards.some((c) => FIXED.has(c))).length >= 2;
  const ungroupable = picked.some((f) => f.cards.length > 1);
  const many = picked.length >= 2;
  const spread = picked.length >= 3;

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
    <div className="tw-toolbar" onPointerDown={(e) => e.stopPropagation()}>
      <span className="tw-toolbar-hint">{picked.length ? `${picked.length} selecionado(s) · Shift+clique soma` : "Clique para selecionar · Shift+clique soma · arraste e redimensione pelo canto"}</span>
      <button type="button" disabled={!groupable} onClick={onGroup}>Agrupar</button>
      <button type="button" disabled={!ungroupable} onClick={onUngroup}>Desagrupar</button>
      <button type="button" disabled={!many} onClick={() => onArrange("left")}>Alinhar à esquerda</button>
      <button type="button" disabled={!many} onClick={() => onArrange("top")}>Alinhar ao topo</button>
      <button type="button" disabled={!spread} onClick={() => onArrange("horizontal")}>Distribuir ↔</button>
      <button type="button" disabled={!spread} onClick={() => onArrange("vertical")}>Distribuir ↕</button>
      <button type="button" disabled={!many} onClick={() => onArrange("size")}>Mesmo tamanho</button>
      <span className="tw-toolbar-sep" />
      <button type="button" onClick={copy}>{copied ? "Link copiado" : "Copiar link para o OBS"}</button>
      <button type="button" onClick={onReset}>Restaurar</button>
      <button type="button" onClick={onClose}>Concluir</button>
    </div>
  );
}

export const BOARD_CSS = `
.tw-stage { position: relative; flex: none; width: ${STAGE.w}px; height: ${STAGE.h}px; transform-origin: center; }
.tw-tile { position: absolute; display: flex; flex-direction: column; }
.tw-tile > .tw-panel, .tw-tile > .tw-header, .tw-tile > .tw-game { flex: 1; min-height: 0; }
.tw-tile[data-edit] { cursor: move; user-select: none; }
.tw-tile[data-edit] > :not(.tw-grip) { pointer-events: none; }
.tw-tile[data-edit]::after { content: ""; position: absolute; inset: -3px; border: 1px dashed color-mix(in srgb, var(--yellow) 60%, transparent); border-radius: 14px; pointer-events: none; }
.tw-tile[data-selected]::after { border: 2px solid var(--yellow); }
.tw-grip { position: absolute; right: -7px; bottom: -7px; width: 16px; height: 16px; border-radius: 4px; background: var(--yellow); cursor: nwse-resize; z-index: 2; }
.tw-toolbar { position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); z-index: 20; display: flex; align-items: center; gap: 6px; padding: 8px 10px; border-radius: 10px; border: 1px solid var(--line); background: var(--panel); box-shadow: 0 10px 30px rgba(0,0,0,.5); white-space: nowrap; font-size: 13px; color: var(--text-2); }
.tw-toolbar button { border: 1px solid var(--line); background: var(--inner); color: var(--text); border-radius: 6px; padding: 5px 10px; font-size: 12px; cursor: pointer; }
.tw-toolbar button:hover:not(:disabled) { border-color: var(--yellow); }
.tw-toolbar button:disabled { opacity: .4; cursor: not-allowed; }
.tw-toolbar-hint { margin-right: 6px; }
.tw-toolbar-sep { width: 1px; align-self: stretch; background: var(--line); margin: 0 4px; }
`;
