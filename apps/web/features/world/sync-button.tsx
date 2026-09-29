"use client";

import { CloudDownload, RefreshCw } from "lucide-react";
import { ActionButton } from "@/components/ui/action-button";

export function WorldSyncButton({ ready }: { ready: boolean }) {
  const Icon = ready ? RefreshCw : CloudDownload;
  return (
    <ActionButton path="/api/v1/world/sync" variant={ready ? "outline" : "default"} done={() => "Dados do mundo atualizados"}>
      <Icon className="size-4" strokeWidth={1.75} />
      {ready ? "Atualizar mundo" : "Baixar dados do mundo"}
    </ActionButton>
  );
}
