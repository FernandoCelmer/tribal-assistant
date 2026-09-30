import { Bot, CircleCheck, CircleX, Coins, Hammer, Settings, ShieldBan, Swords } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/page";
import { Writable } from "@/components/layout/read-only";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { buttonVariants } from "@/components/ui/button";
import { Stat } from "@/components/ui/stat";
import { AgentCards, DecisionTimeline, LiveFeed, LiveStatus, RunButtons, RunsTable, VillagePlans } from "@/features/agents";
import { maybe, server } from "@/lib/api";
import { num } from "@/lib/format";

export default async function AgentsPage() {
  const [live, stats, plans, runs, config, history] = await Promise.all([
    maybe(server.GET("/api/v1/agents/live")),
    maybe(server.GET("/api/v1/agents/stats", { params: { query: { hours: 24 } } })),
    maybe(server.GET("/api/v1/agents/plans")),
    maybe(server.GET("/api/v1/agents/runs", { params: { query: { limit: 200 } } })),
    maybe(server.GET("/api/v1/agents/config")),
    maybe(server.GET("/api/v1/agents/coordination/history", { params: { query: { limit: 48 } } })),
  ]);

  const brain = config ? (config.brain === "llm" ? `IA · ${config.model ?? config.provider}` : "regras fixas") : "cérebro —";
  const known = (config?.agents ?? []).map((a) => (a as { key?: string }).key).filter((k): k is string => !!k);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Agentes"
        description="Cada especialista observa uma parte da aldeia; o coordenador decide o que roda."
        shortDescription="Especialistas, rodadas e raciocínio ao vivo."
        actions={
          <>
            <Writable>
              <Link href="/settings" className={buttonVariants({ variant: "ghost", className: "hidden md:inline-flex" })}>
                <Settings className="size-4" strokeWidth={1.75} />
                Configurar
              </Link>
            </Writable>
            <RunButtons />
          </>
        }
      />

      <LiveStatus initial={live} brain={brain} />

      <div className="flex justify-end"><AutoRefresh every={30_000} /></div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 2xl:grid-cols-6">
        <Stat label="Rodadas (24h)" value={num(stats?.runs)} icon={Bot} hint={stats?.runs_failed ? `${stats.runs_failed} falharam` : "nenhuma falha"} tone={stats?.runs_failed ? "bad" : undefined} />
        <Stat label="Ações feitas" value={num(stats?.actions_ok)} icon={CircleCheck} />
        <Stat label="Recusadas" value={num(stats?.actions_refused)} icon={ShieldBan} hint="barradas pelas travas" tone={stats?.actions_refused ? "warn" : undefined} />
        <Stat label="Falhas" value={num(stats?.actions_failed)} icon={CircleX} tone={stats?.actions_failed ? "bad" : undefined} />
        <Stat label="Obras e tropas" value={num((stats?.builds ?? 0) + (stats?.recruits ?? 0))} icon={Hammer} hint={stats ? `${stats.builds} obras · ${stats.recruits} recrutamentos` : undefined} />
        <Stat label="Saques" value={num(stats?.attacks)} icon={Swords} hint={stats ? <span className="inline-flex items-center gap-1"><Coins className="size-3" />{num(stats.tokens_in + stats.tokens_out)} tokens</span> : undefined} />
      </div>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold">Especialistas <span className="font-normal text-secondary">· últimas 24h</span></h2>
        <AgentCards stats={stats?.agents ?? []} known={known} />
      </section>

      <DecisionTimeline history={history ?? []} />

      <VillagePlans plans={plans ?? []} />

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <RunsTable runs={runs ?? []} />
        <LiveFeed />
      </div>
    </div>
  );
}
