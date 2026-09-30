"use client";

import { Play, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { confirmDialog } from "@/components/ui/dialog-host";
import { toast } from "@/components/ui/toast";
import type { Schemas } from "@/lib/api";
import { errorText } from "@/lib/errors";

type Report = Schemas["AgentRunOut"];

export function RunButtons() {
  const router = useRouter();
  const [busy, setBusy] = useState<"sim" | "live" | null>(null);

  const run = async (dry: boolean) => {
    if (!dry && !(await confirmDialog({ title: "Rodar os agentes no jogo agora?", description: "Eles podem construir, recrutar, coletar e saquear bárbaras de verdade, sem simulação.", confirmLabel: "Rodar agora" }))) return;
    setBusy(dry ? "sim" : "live");
    toast(dry ? "Simulando rodada… acompanhe ao vivo" : "Rodada em andamento… acompanhe ao vivo");
    try {
      const response = await fetch("/api/v1/agents/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dry_run: dry }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(errorText(body, response.status));
      const report = body as Report;
      if (report.error) toast(report.error, "error");
      else toast(`Rodada ${report.run_id} concluída`);
      router.push(`/agents/${report.run_id}`);
    } catch (err) {
      toast((err as Error).message, "error");
      router.refresh();
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <Button variant="outline" loading={busy === "sim"} disabled={busy !== null} onClick={() => run(true)}>
        {busy !== "sim" && <Play className="size-4" strokeWidth={1.75} />}
        Simular rodada
      </Button>
      <Button loading={busy === "live"} disabled={busy !== null} onClick={() => run(false)}>
        {busy !== "live" && <Zap className="size-4" strokeWidth={1.75} />}
        Rodar agora
      </Button>
    </>
  );
}
