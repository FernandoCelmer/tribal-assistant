import { Bot, CalendarClock, Compass, Crosshair, Hand } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/page";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { BudgetPanel, DeferredTable, ExecutedTable, InsightsTable, NextAction, RoleSelect, SpecialistsTable, VillagePicker, type RoundData } from "@/features/strategy";
import { maybe, server } from "@/lib/api";
import { relative, short } from "@/lib/format";
import { ROLES } from "@/lib/game";

export default async function StrategyPage({ searchParams }: { searchParams: Promise<{ village?: string }> }) {
  const [{ village: wanted }, rounds, proposers] = await Promise.all([
    searchParams,
    maybe(server.GET("/api/v1/agents/coordination")),
    maybe(server.GET("/api/v1/agents/proposers")),
  ]);

  const list = rounds ?? [];
  const round = list.find((r) => String(r.village_id) === wanted) ?? list[0];
  const titles = new Map((proposers ?? []).map((p) => [p.key, p.title]));
  const who = (key?: string) => (key ? titles.get(key) ?? key : "—");

  const header = (
    <PageHeader
      title="Estratégia"
      description="O coordenador compara as propostas dos especialistas, reserva recursos e explica o que adiou."
      shortDescription="Papel, próxima jogada e o que foi adiado."
      actions={list.length > 1 && round ? <VillagePicker villages={list.map((r) => ({ id: r.village_id, name: r.village }))} value={round.village_id} /> : undefined}
    />
  );

  if (!round) {
    return (
      <div className="space-y-6">
        {header}
        <Panel>
          <EmptyState
            icon={Compass}
            title="Nenhuma rodada do coordenador ainda"
            text="Rode os agentes para o coordenador decidir o papel de cada aldeia."
            action={<Link href="/agents" className={buttonVariants({ variant: "outline", size: "sm" })}><Bot className="size-4" strokeWidth={1.75} />Ir para Agentes</Link>}
          />
        </Panel>
        {proposers && proposers.length > 0 && <SpecialistsTable proposers={proposers} />}
      </div>
    );
  }

  const data = round.data as RoundData;
  const role = round.role || data.role || "";
  const mode = round.mode || data.mode || "";
  const goal = round.goal || data.goal || "";

  return (
    <div className="space-y-6">
      {header}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2 text-sm">
          <span className="truncate font-medium">{round.village || `Aldeia ${round.village_id}`}</span>
          <Link href={`/agents/${round.run_id}`} className="font-mono text-[12px] text-secondary underline-offset-4 hover:text-foreground hover:underline">rodada {short(round.created_at)}</Link>
        </div>
        <AutoRefresh every={20_000} />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat label="Papel" value={ROLES[role] ?? role} icon={round.manual_role ? Hand : Crosshair} hint={round.manual_role ? "escolhido por você" : "escolhido pelo coordenador"} />
        <Stat label="Modo desta rodada" value={ROLES[mode] ?? mode} icon={Compass} hint={goal || undefined} tone={mode === "emergency" ? "bad" : undefined} />
        <Stat label="Próxima reavaliação" value={<span suppressHydrationWarning>{relative(round.next_review_at)}</span>} icon={CalendarClock} hint={round.next_review_at ? short(round.next_review_at) : "sem data"} />
      </div>

      <Panel className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-semibold">
            Fixar papel
            {round.manual_role && <Badge tone="warning">manual</Badge>}
          </div>
          <p className="mt-0.5 text-[13px] text-secondary">Automático deixa o coordenador escolher a cada rodada; fixar mantém o papel até você mudar.</p>
        </div>
        <RoleSelect key={`${round.village_id}-${role}-${round.manual_role}`} villageId={round.village_id} role={role} manual={round.manual_role ?? false} />
      </Panel>

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(320px,2fr)]">
        <NextAction entry={data.next_action} who={who} />
        <BudgetPanel budget={data.budget} constraints={data.constraints} />
      </div>

      <ExecutedTable entries={data.executed ?? []} who={who} />

      <DeferredTable entries={data.deferred ?? []} who={who} villageId={round.village_id} />

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-2">
        <InsightsTable insights={data.insights ?? []} />
        <SpecialistsTable proposers={proposers ?? []} />
      </div>
    </div>
  );
}
