import { CloudDownload, Map as MapIcon } from "lucide-react";
import { PageHeader } from "@/components/layout/page";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { pickVillage } from "@/features/village";
import { NearbyFilters, NearbyTable, WorldSyncButton, parseKind, parseRadius } from "@/features/world";
import { maybe, server } from "@/lib/api";
import { num, relative } from "@/lib/format";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function SurroundingsPage({ searchParams }: Props) {
  const [params, overview, world] = await Promise.all([
    searchParams,
    maybe(server.GET("/api/v1/game/overview")),
    maybe(server.GET("/api/v1/world/status")),
  ]);
  const villages = (overview?.villages ?? []).map((v) => ({ id: v.id, name: v.name, coords: v.coords }));
  const village = pickVillage(villages, params.village);
  const kind = parseKind(first(params.kind));
  const radius = parseRadius(first(params.radius));
  const ready = !!world?.fetched_at;

  const rows = village && ready
    ? await maybe(server.GET("/api/v1/world/nearby", { params: { query: { village_id: village.id, kind, radius, limit: 200 } } }))
    : null;

  const sync = <WorldSyncButton ready={ready} />;

  const description = world && ready
    ? `${num(world.villages)} aldeias · ${num(world.players)} jogadores · velocidade ${world.speed ?? "—"}x · dados ${relative(world.fetched_at)}`
    : "Aldeias ao redor, distância e tempo de marcha.";

  return (
    <div className="space-y-6">
      <PageHeader title="Arredores" description={description} shortDescription="Aldeias ao redor e tempo de marcha." actions={sync} />

      {!village ? (
        <Panel><EmptyState icon={MapIcon} title="Nenhuma aldeia sincronizada" text="Sincronize uma aldeia na Visão geral para ver os arredores." /></Panel>
      ) : !ready ? (
        <Panel><EmptyState icon={CloudDownload} title="Sem dados do mundo" text="Baixe o mapa do mundo para listar as aldeias próximas." /></Panel>
      ) : (
        <>
          <NearbyFilters villages={villages} village={village.id} kind={kind} radius={radius} />
          {rows ? (
            <NearbyTable rows={rows} radius={radius} description={`a partir de ${village.name} (${village.coords})`} />
          ) : (
            <Panel><EmptyState icon={MapIcon} title="Não foi possível carregar os arredores" text="Verifique se a API está no ar e tente de novo." /></Panel>
          )}
        </>
      )}
    </div>
  );
}
