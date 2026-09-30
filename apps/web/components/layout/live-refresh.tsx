"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { useEvents } from "@/features/agents/events";

const TRIGGERS = new Set(["sync", "decision", "run_finished"]);
const DEBOUNCE = 1_500;
const MIN_GAP = 4_000;
const FALLBACK = 60_000;

export function LiveRefresh() {
  const router = useRouter();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const last = useRef(0);

  const refresh = () => {
    if (document.visibilityState !== "visible") return;
    if (document.querySelector('[role="listbox"], [role="dialog"]')) {
      schedule();
      return;
    }
    last.current = Date.now();
    router.refresh();
  };

  const schedule = () => {
    if (timer.current) clearTimeout(timer.current);
    const wait = Math.max(DEBOUNCE, MIN_GAP - (Date.now() - last.current));
    timer.current = setTimeout(refresh, wait);
  };

  useEvents((event) => {
    if (TRIGGERS.has(event.kind)) schedule();
  });

  useEffect(() => {
    const onVisible = () => document.visibilityState === "visible" && schedule();
    const fallback = setInterval(() => Date.now() - last.current >= FALLBACK && refresh(), FALLBACK);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(fallback);
      document.removeEventListener("visibilitychange", onVisible);
      if (timer.current) clearTimeout(timer.current);
    };
  });

  return null;
}
