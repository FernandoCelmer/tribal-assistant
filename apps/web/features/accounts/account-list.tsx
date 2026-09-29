"use client";

import { AppWindow, EyeOff, KeyRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PageFooter, PageScope, PageSlice } from "@/components/ui/pagination";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { toast } from "@/components/ui/toast";
import { Switch } from "@/features/settings/switch";
import type { Schemas } from "@/lib/api";
import { ApiError, errorText } from "@/lib/errors";
import { num } from "@/lib/format";
import { cn } from "@/lib/utils";

type Account = Schemas["AccountOut"];

export function AccountList({ accounts, current }: { accounts: Account[]; current: number | null }) {
  const router = useRouter();
  const [busy, setBusy] = useState<number | null>(null);
  const [local, setLocal] = useState<Record<number, boolean>>({});
  const playing = accounts.filter((a) => local[a.id] ?? a.enabled).length;

  const toggle = async (account: Account, enabled: boolean) => {
    setBusy(account.id);
    setLocal((m) => ({ ...m, [account.id]: enabled }));
    try {
      const response = await fetch(`/api/v1/accounts/${account.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new ApiError(response.status, errorText(result, response.status));
      toast(enabled ? `${account.name} voltou a jogar` : `${account.name} pausada`);
      router.refresh();
    } catch (err) {
      setLocal((m) => ({ ...m, [account.id]: account.enabled }));
      toast((err as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Panel>
      <PanelHeader
        title={<><KeyRound className="size-4 text-secondary" strokeWidth={1.75} />Contas</>}
        description="Cada conta joga com o próprio navegador e os próprios dados."
        aside={<Badge>{num(playing)} de {num(accounts.length)} jogando</Badge>}
      />
      {accounts.length === 0 ? (
        <EmptyState icon={KeyRound} title="Nenhuma conta cadastrada" text="Adicione a primeira conta no formulário ao lado." />
      ) : (
        <PageScope total={accounts.length}>
        <ul className="divide-y divide-border-subtle">
          <PageSlice>{accounts.map((a) => {
            const on = local[a.id] ?? a.enabled;
            const selected = current === a.id;
            return (
              <li key={a.id} className="flex min-h-[68px] items-center gap-3 px-4 py-3">
                <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-md border font-mono text-[12px] uppercase", on ? "border-border-hover text-foreground" : "border-border-subtle text-muted-foreground")}>
                  {a.server.slice(0, 5)}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-sm font-medium">{a.name}</span>
                    {selected && <Badge tone="ok" className="h-5 px-2 text-[11px]">no painel</Badge>}
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[12px] text-secondary">
                    <span className="truncate font-mono">{a.username}</span>
                    <span className="truncate">{a.world_url.replace(/^https?:\/\//, "")}</span>
                    <span className="inline-flex items-center gap-1 text-muted-foreground">
                      {a.headless ? <EyeOff className="size-3" strokeWidth={1.75} /> : <AppWindow className="size-3" strokeWidth={1.75} />}
                      {a.headless ? "sem janela" : "com janela"}
                    </span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2.5">
                  <span className={cn("hidden text-[12px] sm:inline", on ? "text-foreground" : "text-muted-foreground")}>{on ? "jogando" : "pausada"}</span>
                  <Switch checked={on} busy={busy === a.id} onChange={(v) => toggle(a, v)} label={on ? `Pausar ${a.name}` : `Voltar a jogar com ${a.name}`} />
                </div>
              </li>
            );
          })}</PageSlice>
        </ul>
        <PageFooter noun={["conta", "contas"]} />
        </PageScope>
      )}
    </Panel>
  );
}
