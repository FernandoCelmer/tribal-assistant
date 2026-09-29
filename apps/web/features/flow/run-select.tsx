"use client";

import { Select } from "@/components/ui/select";
import { useMounted, useQueryNav } from "@/features/charts";
import type { Schemas } from "@/lib/api";
import { short } from "@/lib/format";

type Run = Schemas["RunOut"];

function name(run: Run): string {
  const brain = run.brain === "llm" ? run.model || "IA" : "regras";
  return `${short(run.started_at)} · ${brain}${run.dry_run ? " · simulação" : ""}`;
}

export function RunSelect({ runs, value }: { runs: Run[]; value: string }) {
  const { set, pending } = useQueryNav();
  const mounted = useMounted();
  const options = [
    { value: "", label: "Todas as rodadas do período" },
    ...runs.map((r) => ({ value: r.run_id, label: mounted ? name(r) : r.run_id.slice(0, 8), hint: r.status === "failed" ? "falhou" : undefined })),
  ];
  return <Select aria-label="Rodada" value={value} onChange={(v) => set({ run: v })} options={options} size="lg" className={pending ? "opacity-60 md:h-9 md:w-72" : "md:h-9 md:w-72"} />;
}
