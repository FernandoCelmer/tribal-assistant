import { Workflow } from "lucide-react";
import { PageHeader } from "@/components/layout/page";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { PeriodControl, period } from "@/features/charts";
import { FlowView, RunSelect } from "@/features/flow";
import { maybe, server } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FlowPage({ searchParams }: { searchParams: Promise<{ hours?: string; run?: string }> }) {
  const query = await searchParams;
  const range = period(query.hours);
  const run = query.run ?? "";

  const [flow, runs] = await Promise.all([
    maybe(server.GET("/api/v1/agents/flow", { params: { query: { hours: Number(range), run_id: run || null } } })),
    maybe(server.GET("/api/v1/agents/runs", { params: { query: { limit: 50 } } })),
  ]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Grafos"
        description="Como cada agente decide: de quem partiu a chamada, qual ferramenta usou e o que aconteceu no jogo."
        shortDescription="Agentes → ferramentas → resultados."
        actions={
          <div className="flex w-full flex-col gap-2 md:w-auto md:flex-row">
            <PeriodControl value={range} clear={["run"]} />
            <RunSelect runs={runs ?? []} value={run} />
          </div>
        }
      />

      <div className="flex justify-end"><AutoRefresh every={60_000} /></div>

      {flow ? <FlowView data={flow} /> : (
        <Panel><EmptyState icon={Workflow} title="Grafo indisponível" text="A API não respondeu. Confira se o servidor está no ar." /></Panel>
      )}
    </div>
  );
}
