import { Coins, Mail, ScrollText, Trophy } from "lucide-react";
import { Cost } from "@/components/game/resource";
import { PageHeader } from "@/components/layout/page";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { Stat } from "@/components/ui/stat";
import { ReportsTable } from "@/features/reports";
import { maybe, server } from "@/lib/api";
import { num, percent } from "@/lib/format";

export default async function ReportsPage() {
  const overview = await maybe(server.GET("/api/v1/game/overview"));
  const reports = overview?.reports ?? [];
  const fresh = reports.filter((r) => r.is_new).length;
  const battles = reports.filter((r) => r.result && r.result !== "blue");
  const wins = battles.filter((r) => r.result === "green" || r.result === "yellow").length;
  const loot = reports.reduce((sum, r) => ({ wood: sum.wood + r.loot_wood, clay: sum.clay + r.loot_clay, iron: sum.iron + r.loot_iron }), { wood: 0, clay: 0, iron: 0 });
  const total = loot.wood + loot.clay + loot.iron;

  return (
    <div className="space-y-6">
      <PageHeader title="Relatórios" description="Resultados dos ataques, alvos e saque de cada batalha." shortDescription="Ataques e saque." />

      <div className="flex justify-end"><AutoRefresh every={30_000} /></div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Relatórios" value={num(reports.length)} icon={ScrollText} hint={`${num(battles.length)} batalhas`} />
        <Stat label="Novos" value={num(fresh)} icon={Mail} tone={fresh ? "warn" : undefined} hint={fresh ? "ainda não lidos" : "tudo lido"} />
        <Stat label="Taxa de vitória" value={battles.length ? percent(wins / battles.length) : "—"} icon={Trophy} tone={battles.length && wins === battles.length ? "ok" : undefined} hint={`${num(wins)} de ${num(battles.length)}`} />
        <Stat label="Saque total" value={num(total)} icon={Coins} hint={<Cost wood={loot.wood} clay={loot.clay} iron={loot.iron} className="gap-x-2 text-[12px]" />} />
      </div>

      <ReportsTable reports={reports} />
    </div>
  );
}
