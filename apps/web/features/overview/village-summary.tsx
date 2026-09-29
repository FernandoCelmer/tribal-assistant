import { Castle, Users } from "lucide-react";
import { Meter, ResourceIcon } from "@/components/game/resource";
import { BuildingIcon, Coords } from "@/components/game/icons";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import type { Schemas } from "@/lib/api";
import { num } from "@/lib/format";
import type { Resource } from "@/lib/game";

type Village = Schemas["VillageOverview"];

export function VillageSummary({ village }: { village: Village }) {
  const stock: Record<Resource, number> = { wood: village.wood, clay: village.clay, iron: village.iron };
  const production: Record<Resource, number> = { wood: village.wood_prod, clay: village.clay_prod, iron: village.iron_prod };
  const queue = village.buildings.filter((b) => b.queued_level);

  return (
    <Panel>
      <PanelHeader
        title={<><Castle className="size-4 text-secondary" strokeWidth={1.75} />{village.name}</>}
        description={<span className="inline-flex items-center gap-3"><Coords value={village.coords} /><span>{num(village.points)} pontos</span></span>}
        aside={<Badge><Users className="mr-1 size-3" />{num(village.pop_current)}/{num(village.pop_max)}</Badge>}
      />
      <PanelBody className="space-y-5">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {(Object.keys(stock) as Resource[]).map((kind) => (
            <div key={kind} className="rounded-md border border-border-subtle p-3">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-[13px] text-secondary"><ResourceIcon kind={kind} />{num(stock[kind])}</span>
                <span className="font-mono text-[11px] text-muted-foreground">+{num(production[kind])}/h</span>
              </div>
              <div className="mt-2"><Meter kind={kind} value={stock[kind]} max={village.storage} /></div>
            </div>
          ))}
        </div>
        <div className="text-[12px] text-muted-foreground">Armazém {num(village.storage)}</div>

        <div>
          <div className="mb-2 text-xs font-medium text-muted-foreground">Fila de obras</div>
          {queue.length ? (
            <ul className="space-y-2">
              {queue.map((b) => (
                <li key={b.name} className="flex items-center gap-3 text-sm">
                  <BuildingIcon name={b.name} level={b.level} className="size-6" />
                  <span className="flex-1">{b.label} <span className="text-secondary">→ {b.queued_level}</span></span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-secondary">Fila vazia.</p>
          )}
        </div>

      </PanelBody>
    </Panel>
  );
}
