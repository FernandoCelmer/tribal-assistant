"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function AutoRefresh({ every = 20_000, label = true }: { every?: number; label?: boolean }) {
  const router = useRouter();
  const [at, setAt] = useState<string>("");

  useEffect(() => {
    setAt(new Date().toLocaleTimeString("pt-BR"));
    const id = setInterval(() => {
      if (document.visibilityState !== "visible") return;
      router.refresh();
      setAt(new Date().toLocaleTimeString("pt-BR"));
    }, every);
    return () => clearInterval(id);
  }, [every, router]);

  if (!label) return null;
  return (
    <span className="inline-flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
      <span aria-hidden className="live-dot size-1.5 rounded-full bg-status-ok" />
      atualizado {at}
    </span>
  );
}
