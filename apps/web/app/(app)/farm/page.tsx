import { Clock, Coins, Flag, Power } from "lucide-react";
import { PageHeader } from "@/components/layout/page";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { Stat } from "@/components/ui/stat";
import { FarmForm, FarmTable, TickButton } from "@/features/farm";
import { maybe, server } from "@/lib/api";
import { num, relative, utc } from "@/lib/format";

export default async function FarmPage() {
  const targets = (await maybe(server.GET("/api/v1/farm/targets"))) ?? [];
  const active = targets.filter((t) => t.enabled).length;
  const loot = targets.reduce((sum, t) => sum + t.last_loot, 0);
  const last = targets
    .map((t) => t.last_attack_at)
    .filter((v): v is string => !!v)
    .sort((a, b) => utc(b).getTime() - utc(a).getTime())[0];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Farm"
        description="Aldeias bárbaras saqueadas em rodízio pelo assistente de saque."
        shortDescription="Alvos de saque."
        actions={<TickButton disabled={!active} />}
      />

      <div className="flex justify-end"><AutoRefresh every={20_000} /></div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Alvos" value={num(targets.length)} icon={Flag} />
        <Stat label="Ativos" value={num(active)} icon={Power} tone={targets.length && !active ? "warn" : undefined} hint={targets.length - active ? `${num(targets.length - active)} pausados` : "todos ativos"} />
        <Stat label="Último saque somado" value={num(loot)} icon={Coins} hint="soma do último ataque de cada alvo" />
        <Stat label="Último ataque" value={last ? relative(last).replace("há ", "") : "—"} icon={Clock} hint={last ? "atrás" : "nenhum ataque ainda"} />
      </div>

      <FarmForm />

      <FarmTable targets={targets} />
    </div>
  );
}
