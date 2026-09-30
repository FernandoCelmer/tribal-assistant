import { Ban, Castle, ChartLine, Coins, Hammer, ScrollText, Sparkles, Swords, TriangleAlert, Users, Workflow } from "lucide-react";
import { PageHeader } from "@/components/layout/page";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { AgentMetrics, PeriodControl, VillageEvolution, compact, period } from "@/features/charts";
import { maybe, server } from "@/lib/api";
import { num } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function ChartsPage({ searchParams }: { searchParams: Promise<{ hours?: string; village?: string }> }) {
  const query = await searchParams;
  const range = period(query.hours);
  const hours = Number(range);
  const overview = await maybe(server.GET("/api/v1/game/overview"));
  const villages = (overview?.villages ?? []).map((v) => ({ id: v.id, name: v.name, coords: v.coords }));
  const asked = Number(query.village);
  const village = villages.find((v) => v.id === asked)?.id ?? villages[0]?.id ?? null;

  const [stats, history] = await Promise.all([
    maybe(server.GET("/api/v1/agents/stats", { params: { query: { hours } } })),
    maybe(server.GET("/api/v1/game/history", { params: { query: { hours, village_id: village } } })),
  ]);

  const tokens = (stats?.tokens_in ?? 0) + (stats?.tokens_out ?? 0);
  const breakdown = [
    { label: "Construções", value: stats?.builds, hint: "na fila", icon: Hammer },
    { label: "Recrutamentos", value: stats?.recruits, hint: "lotes", icon: Users },
    { label: "Saques", value: stats?.attacks, hint: "ataques enviados", icon: Swords },
    { label: "Missões", value: stats?.quests, hint: "concluídas ou coletadas", icon: ScrollText },
    { label: "Falhas no jogo", value: stats?.actions_failed, hint: "o jogo não aceitou", icon: TriangleAlert },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Gráficos"
        description="O que os agentes fizeram e como a aldeia evoluiu no período."
        shortDescription="Agentes e evolução da aldeia."
        actions={<PeriodControl value={range} />}
      />

      <div className="flex justify-end"><AutoRefresh every={60_000} /></div>

      {stats ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Rodadas" value={num(stats.runs)} hint={stats.runs_failed ? `${num(stats.runs_failed)} com falha` : "nenhuma falha"} tone={stats.runs_failed ? "bad" : undefined} icon={Workflow} />
            <Stat label="Ações feitas" value={num(stats.actions_ok)} hint="obras, tropas, saques, missões" icon={Sparkles} />
            <Stat label="Recusadas pelas travas" value={num(stats.actions_refused)} hint="segurança funcionando" tone={stats.actions_refused ? "warn" : undefined} icon={Ban} />
            <Stat label="Tokens de IA" value={compact(tokens)} hint={`${num(stats.tokens_in)} entrada · ${num(stats.tokens_out)} saída`} icon={Coins} />
          </div>

          <Panel>
            <dl className="grid grid-cols-2 divide-border-subtle sm:grid-cols-3 lg:grid-cols-5 lg:divide-x">
              {breakdown.map((b) => {
                const Icon = b.icon;
                return (
                  <div key={b.label} className="flex items-center gap-3 px-4 py-3">
                    <Icon className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} aria-hidden />
                    <div className="min-w-0">
                      <dt className="truncate text-[12px] text-secondary">{b.label}</dt>
                      <dd className="text-lg font-semibold leading-6 tabular-nums">{num(b.value)}</dd>
                      <dd className="truncate text-[11px] text-muted-foreground">{b.hint}</dd>
                    </div>
                  </div>
                );
              })}
            </dl>
          </Panel>

          <AgentMetrics stats={stats} hours={hours} />
        </>
      ) : (
        <Panel><EmptyState icon={ChartLine} title="Métricas indisponíveis" text="A API não respondeu. Confira se o servidor está no ar." /></Panel>
      )}

      {villages.length ? (
        <VillageEvolution rows={history ?? []} villages={villages} village={village} />
      ) : (
        <Panel><EmptyState icon={Castle} title="Nenhuma aldeia sincronizada" text="Sincronize a conta para acompanhar pontos, recursos, população e tropas." /></Panel>
      )}
    </div>
  );
}
