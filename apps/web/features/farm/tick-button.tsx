"use client";

import { Swords } from "lucide-react";
import { ActionButton } from "@/components/ui/action-button";

type Tick = { dispatched?: number; skipped?: number; errors?: string[] };

export function TickButton({ disabled }: { disabled?: boolean }) {
  const done = (result: unknown) => {
    const r = (result ?? {}) as Tick;
    const errors = r.errors ?? [];
    return `Enviados: ${r.dispatched ?? 0} · pulados: ${r.skipped ?? 0}${errors.length ? ` · erros: ${errors.join("; ")}` : ""}`;
  };

  return (
    <ActionButton path="/api/v1/farm/tick" disabled={disabled} done={done}>
      <Swords className="size-4" strokeWidth={1.75} />
      Rodar saque agora
    </ActionButton>
  );
}
