import { Ban, CircleCheck, Target, Trophy } from "lucide-react";
import { PageHeader } from "@/components/layout/page";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { Stat } from "@/components/ui/stat";
import { ChallengesTable } from "@/features/challenges";
import { maybe, server } from "@/lib/api";
import { num, relative } from "@/lib/format";

export default async function ChallengesPage() {
  const data = await maybe(server.GET("/api/v1/challenges"));
  const items = data?.items ?? [];
  const summary = data?.summary ?? {};
  const closest = items.filter((c) => !c.done && c.status === "auto" && c.target).toSorted((a, b) => (b.ratio ?? 0) - (a.ratio ?? 0))[0];

  return (
    <div className="space-y-6">
      <PageHeader title="Desafios" description="As conquistas do jogo, o progresso de cada uma e qual agente persegue ou por que fica de fora." shortDescription="Conquistas e progresso." />

      <div className="flex justify-end"><AutoRefresh every={60_000} /></div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Automáticos" value={num(summary.auto ?? 0)} icon={Target} hint="os agentes perseguem sozinhos" />
        <Stat label="Mais perto" value={closest ? `${num(closest.current ?? 0)}/${num(closest.target ?? 0)}` : "—"} icon={Trophy} tone={closest && (closest.ratio ?? 0) >= 0.9 ? "ok" : undefined} hint={closest?.name ?? "nenhum em andamento"} />
        <Stat label="Fora" value={num((summary.blocked ?? 0) + (summary.social ?? 0))} icon={Ban} hint={`${num(summary.social ?? 0)} dependem de você`} />
        <Stat label="Concluídos" value={num(summary.done ?? 0)} icon={CircleCheck} hint={data?.updated_at ? `lido ${relative(data.updated_at)}` : "ainda não lido"} />
      </div>

      <ChallengesTable items={items} />
    </div>
  );
}
