import { Cpu, Globe } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import type { Schemas } from "@/lib/api";

type Info = Schemas["SystemInfo"];

function Grid({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-4 p-4 text-sm sm:grid-cols-2">
      {items.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="text-xs text-secondary">{k}</dt>
          <dd className="mt-0.5 break-words">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function AiInfo({ info }: { info: Info["ai"] }) {
  const status = info.active
    ? <Badge tone="success">ativa</Badge>
    : <Badge tone={info.provider === "none" ? "neutral" : "danger"}>{info.error || "desligada"}</Badge>;
  return (
    <Panel>
      <PanelHeader
        title={<><Cpu className="size-4 text-secondary" strokeWidth={1.75} />Provedor de IA</>}
        description={<>Provedor, modelo e chave ficam no <code className="font-mono text-[12px]">.env</code> (<code className="font-mono text-[12px]">AI_PROVIDER</code>, <code className="font-mono text-[12px]">AI_MODEL</code>, <code className="font-mono text-[12px]">AI_API_KEY</code>).</>}
        aside={status}
      />
      <Grid
        items={[
          ["Provedor", <span key="p" className="font-mono">{info.provider}</span>],
          ["Modelo", <span key="m" className="font-mono">{info.model || "—"}</span>],
          ["Endereço", <span key="b" className="font-mono text-[13px] text-secondary">{info.base_url || "padrão do SDK"}</span>],
          ["Chave", info.key_configured ? <Badge key="k" tone="success">configurada</Badge> : <Badge key="k" tone="warning">ausente</Badge>],
        ]}
      />
    </Panel>
  );
}

export function SystemInfo({ info }: { info: Info }) {
  return (
    <Panel>
      <PanelHeader title={<><Globe className="size-4 text-secondary" strokeWidth={1.75} />Sistema</>} aside={<Badge>somente leitura · .env</Badge>} />
      <Grid
        items={[
          ["Mundo", info.server || info.world_url ? <><span className="font-mono">{info.server ?? "—"}</span>{info.world_url && <span className="block text-[13px] text-secondary">{info.world_url}</span>}</> : "—"],
          ["Versão", <span key="v" className="font-mono">v{info.version}</span>],
          ["Sincronização da conta", `a cada ${info.sync_interval_seconds} s`],
          ["Dados do mundo", `a cada ${info.world_sync_interval_minutes} min`],
          ["Horário de silêncio", info.quiet_hours || "nenhum"],
          ["Navegador", info.headless ? "oculto (headless)" : "visível"],
          ["Banco de dados", <span key="d" className="font-mono text-[13px]">{info.database}</span>],
          ["Retenção", `rodadas ${info.trace_retention_days} dias · logs ${info.log_retention_days} dias`],
        ]}
      />
    </Panel>
  );
}
