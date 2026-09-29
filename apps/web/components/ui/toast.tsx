"use client";

import { CircleAlert, CircleCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

type Toast = { id: number; text: string; tone: "info" | "error" };
const EVENT = "tribal-toast";

export function toast(text: string, tone: "info" | "error" = "info") {
  window.dispatchEvent(new CustomEvent<Toast>(EVENT, { detail: { id: Date.now() + Math.random(), text, tone } }));
}

export function Toaster() {
  const [items, setItems] = useState<Toast[]>([]);

  useEffect(() => {
    const add = (e: Event) => {
      const item = (e as CustomEvent<Toast>).detail;
      setItems((list) => [...list.slice(-2), item]);
      setTimeout(() => setItems((list) => list.filter((t) => t.id !== item.id)), 4500);
    };
    window.addEventListener(EVENT, add);
    return () => window.removeEventListener(EVENT, add);
  }, []);

  return (
    <div aria-live="polite" className="pointer-events-none fixed bottom-[calc(96px+env(safe-area-inset-bottom))] right-4 z-50 flex w-[min(380px,calc(100vw-2rem))] flex-col gap-2 md:bottom-6">
      {items.map((t) => (
        <div key={t.id} className={cn("select-in pointer-events-auto flex items-start gap-2.5 rounded-lg border bg-surface px-4 py-3 text-sm", t.tone === "error" ? "border-status-bad/40" : "border-border")}>
          {t.tone === "error" ? <CircleAlert className="mt-0.5 size-4 shrink-0 text-status-bad" /> : <CircleCheck className="mt-0.5 size-4 shrink-0 text-status-ok" />}
          <span className="min-w-0">{t.text}</span>
        </div>
      ))}
    </div>
  );
}
