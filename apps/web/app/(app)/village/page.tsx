import { Castle, Hammer, Shield, Trophy, Users } from "lucide-react";
import { Meter, ResourceIcon } from "@/components/game/resource";
import { PageHeader } from "@/components/layout/page";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { BuildingsTable, RecruitQueue, ScavengePanel, TroopsTable, VillagePicker, VillageTimelapse, pickVillage } from "@/features/village";
import { maybe, server } from "@/lib/api";
import { num, relative } from "@/lib/format";
import { RESOURCES, type Resource } from "@/lib/game";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function VillagePage({ searchParams }: Props) {
  const [params, overview] = await Promise.all([searchParams, maybe(server.GET("/api/v1/game/overview"))]);
  const villages = overview?.villages ?? [];
  const village = pickVillage(villages, params.village);
  const picker = <VillagePicker villages={villages} current={village?.id ?? null} />;

  if (!village) {
    return (
      <div className="space-y-6">
        <PageHeader title="Aldeia" description="Tropas, edifícios e coleta da aldeia." />
        <Panel><EmptyState icon={Castle} title="Nenhuma aldeia sincronizada" text="Sincronize a conta na Visão geral para ver tropas e edifícios." /></Panel>
      </div>
    );
  }

  const frames = (await maybe(server.GET("/api/v1/villages/{village_id}/frames", { params: { path: { village_id: village.id } } }))) ?? [];
  const stock: Record<Resource, number> = { wood: village.wood, clay: village.clay, iron: village.iron };
  const production: Record<Resource, number> = { wood: village.wood_prod, clay: village.clay_prod, iron: village.iron_prod };
  const home = village.units.reduce((sum, u) => sum + u.home, 0);
  const away = village.units.reduce((sum, u) => sum + u.away, 0);
  const queued = village.buildings.filter((b) => b.queued_level).length;
  const ready = village.buildings.filter((b) => b.can_build).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title={village.name}
        description={`${village.coords} · sincronizada ${relative(village.synced_at)}`}
        shortDescription={village.coords}
        actions={villages.length > 1 ? picker : undefined}
      />

      <div className="flex justify-end"><AutoRefresh every={15_000} /></div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Pontos" value={num(village.points)} icon={Trophy} />
        <Stat label="População" value={`${num(village.pop_current)}`} hint={`de ${num(village.pop_max)}`} icon={Users} tone={village.pop_max && village.pop_current / village.pop_max > 0.9 ? "warn" : undefined} />
        <Stat label="Tropas em casa" value={num(home)} hint={away ? `${num(away)} fora` : "nenhuma fora"} icon={Shield} />
        <Stat label="Obras na fila" value={num(queued)} hint={`${num(ready)} prontas para subir`} icon={Hammer} />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {(Object.keys(stock) as Resource[]).map((kind) => (
          <div key={kind} className="rounded-lg border border-border bg-surface p-4">
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 text-sm"><ResourceIcon kind={kind} /><span className="text-secondary">{RESOURCES[kind].label}</span></span>
              <span className="font-mono text-[11px] text-muted-foreground">+{num(production[kind])}/h</span>
            </div>
            <div className="mt-2 flex items-baseline justify-between gap-2">
              <span className="text-lg font-semibold tabular-nums">{num(stock[kind])}</span>
              <span className="font-mono text-[11px] text-muted-foreground">/{num(village.storage)}</span>
            </div>
            <div className="mt-2"><Meter kind={kind} value={stock[kind]} max={village.storage} /></div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <TroopsTable units={village.units} />
        <div className="space-y-4">
          <RecruitQueue orders={village.recruit_orders} />
          <ScavengePanel options={village.scavenge} />
        </div>
      </div>

      <BuildingsTable buildings={village.buildings} />

      <VillageTimelapse key={village.id} frames={frames} />
    </div>
  );
}
