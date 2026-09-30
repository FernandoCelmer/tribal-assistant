import { Compass, Crown, RefreshCw, ScrollText, Shield, Swords, Trophy } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/page";
import { Coords, UnitIcon } from "@/components/game/icons";
import { ActionButton } from "@/components/ui/action-button";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { AccountVillages, VillageSummary } from "@/features/overview";
import { maybe, server } from "@/lib/api";
import { num, relative, when } from "@/lib/format";
import { ROLES } from "@/lib/game";

export default async function OverviewPage() {
  const [overview, status, coordination, quests] = await Promise.all([
    maybe(server.GET("/api/v1/game/overview")),
    maybe(server.GET("/api/v1/assistant/status")),
    maybe(server.GET("/api/v1/agents/coordination")),
    maybe(server.GET("/api/v1/agents/quests")),
  ]);

  const player = overview?.player;
  const villages = overview?.villages ?? [];
  const village = villages[0];
  const roles = Object.fromEntries((coordination ?? []).map((c) => [c.village_id, c.mode]));
  const round = coordination?.find((c) => (c.data?.next_action as { title?: string } | undefined)?.title) ?? coordination?.[0];
  const state = !status ? { label: "sem API", tone: "danger" as const } : !status.playing ? { label: "só painel", tone: "neutral" as const } : !status.running ? { label: "parado", tone: "danger" as const } : !status.agents_enabled ? { label: "agentes desligados", tone: "warning" as const } : { label: "jogando", tone: "success" as const };
  const next = round?.data?.next_action as { title?: string; reason?: string; why?: string } | undefined;
  const incoming = overview?.commands.filter((c) => c.direction === "in") ?? [];
  const protectedUntil = player?.protection_until;

  return (
    <div className="space-y-6">
      <PageHeader
        title={player ? `Olá, ${player.name}` : "Visão geral"}
        description={player ? `Mundo ${player.world} · última sincronização ${relative(player.synced_at)}` : "Nenhuma conta sincronizada ainda."}
        actions={
          <>
            <ActionButton path="/api/v1/assistant/sync" variant="outline" successField="message" success="Sincronizado">
              <RefreshCw className="size-4" strokeWidth={1.75} />
              Sincronizar agora
            </ActionButton>
            <Link href="/strategy" className={buttonVariants({ variant: "default" })}><Compass className="size-4" strokeWidth={1.75} />Estratégia</Link>
          </>
        }
      />

      <div className="flex justify-end"><AutoRefresh /></div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Pontos" value={num(player?.points)} hint={player ? `ranking #${num(player.rank)}` : undefined} icon={Trophy} />
        <Stat label="Aldeias" value={num(player?.villages ?? villages.length)} icon={Crown} />
        <Stat label="Ataques chegando" value={num(incoming.length)} tone={incoming.length ? "bad" : undefined} icon={Swords} hint={incoming.length ? "tropas ficam em casa" : "tudo calmo"} />
        <Stat label="Proteção de iniciante" value={protectedUntil && new Date(protectedUntil) > new Date() ? relative(protectedUntil).replace("em ", "") : "—"} icon={Shield} hint={protectedUntil ? when(protectedUntil) : "sem proteção"} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        {villages.length > 1 ? <AccountVillages villages={villages} commands={overview?.commands ?? []} roles={roles} /> : village ? <VillageSummary village={village} /> : (
          <Panel><EmptyState icon={Crown} title="Nenhuma aldeia sincronizada" text="Suba o servidor e clique em Sincronizar agora." /></Panel>
        )}

        <div className="space-y-4">
          <Panel>
            <PanelHeader title="Assistente" aside={<Badge tone={state.tone}>{state.label}</Badge>} />
            <PanelBody className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-secondary">Sessão no jogo</span><span>{status?.logged_in ? "conectada" : "desconectada"}</span></div>
              <div className="flex justify-between"><span className="text-secondary">Última sincronização</span><span>{relative(status?.last_sync_at)}</span></div>
              {status?.last_error && <p className="rounded-md border border-status-bad/30 bg-status-bad/10 px-3 py-2 text-[13px] text-status-bad">{status.last_error}</p>}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader title="Próxima jogada" description={villages.length > 1 ? round?.village : undefined} aside={round && <Badge>{ROLES[round.mode] ?? round.mode}</Badge>} />
            <PanelBody className="text-sm">
              {next?.title ? (
                <>
                  <div className="font-medium">{next.title}</div>
                  <p className="mt-1 text-secondary">{next.reason}</p>
                  {next.why && <p className="mt-1 text-[13px] text-muted-foreground">adiada: {next.why}</p>}
                </>
              ) : <p className="text-secondary">Sem rodada do coordenador ainda.</p>}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader title="Missões" aside={<Badge>{num(quests?.rewards.length ?? 0)} recompensas</Badge>} />
            <PanelBody>
              <ul className="space-y-2 text-sm">
                {(quests?.quests ?? []).filter((q) => q.state !== "finished").slice(0, 6).map((q) => (
                  <li key={q.quest_id} className="flex items-start gap-2">
                    <ScrollText className="mt-0.5 size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
                    <span className="min-w-0 flex-1">{q.title}<span className="block text-[12px] text-muted-foreground">{q.goals.map((g) => g.title).join(" · ")}</span></span>
                    {q.can_complete && <Badge tone="success">pronta</Badge>}
                  </li>
                ))}
              </ul>
            </PanelBody>
          </Panel>

          {incoming.length > 0 && (
            <Panel>
              <PanelHeader title="Movimentos chegando" />
              <PanelBody>
                <ul className="space-y-2 text-sm">
                  {incoming.map((c, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <UnitIcon name={c.kind === "noble" ? "snob" : "axe"} />
                      <span className="flex-1">{c.label}</span>
                      {c.coords && <Coords value={c.coords} />}
                      <span className="font-mono text-[12px] text-status-bad">{relative(c.arrival_at)}</span>
                    </li>
                  ))}
                </ul>
              </PanelBody>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
