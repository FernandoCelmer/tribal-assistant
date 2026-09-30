import { Castle, Hammer, Swords, Users } from "lucide-react";
import { Meter, ResourceIcon } from "@/components/game/resource";
import { BuildingIcon, Coords } from "@/components/game/icons";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import type { Schemas } from "@/lib/api";
import { num, relative } from "@/lib/format";
import { ROLES, type Resource } from "@/lib/game";

type Village = Schemas["VillageOverview"];
type Command = Schemas["CommandOut"];

const KINDS: Resource[] = ["wood", "clay", "iron"];

function stockOf(village: Village): Record<Resource, number> {
  return { wood: village.wood, clay: village.clay, iron: village.iron };
}

function productionOf(village: Village): Record<Resource, number> {
  return { wood: village.wood_prod, clay: village.clay_prod, iron: village.iron_prod };
}

export function AccountTotals({ villages, incoming }: { villages: Village[]; incoming: number }) {
  const stock = Object.fromEntries(KINDS.map((k) => [k, villages.reduce((sum, v) => sum + stockOf(v)[k], 0)])) as Record<Resource, number>;
  const production = Object.fromEntries(KINDS.map((k) => [k, villages.reduce((sum, v) => sum + productionOf(v)[k], 0)])) as Record<Resource, number>;
  const storage = villages.reduce((sum, v) => sum + v.storage, 0);
  const pop = villages.reduce((sum, v) => sum + v.pop_current, 0);
  const popMax = villages.reduce((sum, v) => sum + v.pop_max, 0);
  const queued = villages.reduce((sum, v) => sum + v.buildings.filter((b) => b.queued_level).length, 0);

  return (
    <Panel>
      <PanelHeader
        title={<><Castle className="size-4 text-secondary" strokeWidth={1.75} />Total da conta</>}
        description={`${num(villages.length)} aldeias · ${num(villages.reduce((sum, v) => sum + v.points, 0))} pontos`}
        aside={<Badge><Users className="mr-1 size-3" />{num(pop)}/{num(popMax)}</Badge>}
      />
      <PanelBody className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {KINDS.map((kind) => (
            <div key={kind} className="rounded-md border border-border-subtle p-3">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-[13px] text-secondary"><ResourceIcon kind={kind} />{num(stock[kind])}</span>
                <span className="font-mono text-[11px] text-muted-foreground">+{num(production[kind])}/h</span>
              </div>
              <div className="mt-2"><Meter kind={kind} value={stock[kind]} max={storage} /></div>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-muted-foreground">
          <span>Armazéns {num(storage)}</span>
          <span>{num(queued)} obra(s) na fila</span>
          <span className={incoming ? "text-status-bad" : undefined}>{num(incoming)} ataque(s) chegando</span>
        </div>
      </PanelBody>
    </Panel>
  );
}

export function VillageCard({ village, role, incoming }: { village: Village; role?: string; incoming: Command[] }) {
  const stock = stockOf(village);
  const production = productionOf(village);
  const queue = village.buildings.filter((b) => b.queued_level);

  return (
    <Panel>
      <PanelHeader
        title={<><Castle className="size-4 text-secondary" strokeWidth={1.75} />{village.name}</>}
        description={<span className="inline-flex items-center gap-3"><Coords value={village.coords} /><span>{num(village.points)} pontos</span></span>}
        aside={
          <span className="inline-flex items-center gap-2">
            {role && <Badge>{ROLES[role] ?? role}</Badge>}
            <Badge><Users className="mr-1 size-3" />{num(village.pop_current)}/{num(village.pop_max)}</Badge>
          </span>
        }
      />
      <PanelBody className="space-y-4">
        <div className="space-y-2">
          {KINDS.map((kind) => (
            <div key={kind} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1">
              <span className="inline-flex items-center gap-2 text-[13px] text-secondary"><ResourceIcon kind={kind} />{num(stock[kind])}</span>
              <span className="font-mono text-[11px] text-muted-foreground">+{num(production[kind])}/h</span>
              <div className="col-span-2"><Meter kind={kind} value={stock[kind]} max={village.storage} /></div>
            </div>
          ))}
          <div className="text-[12px] text-muted-foreground">Armazém {num(village.storage)}</div>
        </div>

        <div>
          <div className="mb-2 inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground"><Hammer className="size-3.5" strokeWidth={1.75} />Fila de obras</div>
          {queue.length ? (
            <ul className="space-y-1.5">
              {queue.map((b) => (
                <li key={b.name} className="flex items-center gap-2 text-sm">
                  <BuildingIcon name={b.name} level={b.level} className="size-5" />
                  <span className="min-w-0 flex-1 truncate">{b.label} <span className="text-secondary">→ {b.queued_level}</span></span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-secondary">Fila vazia.</p>
          )}
        </div>

        {incoming.length > 0 && (
          <div>
            <div className="mb-2 inline-flex items-center gap-1.5 text-xs font-medium text-status-bad"><Swords className="size-3.5" strokeWidth={1.75} />Ataques chegando</div>
            <ul className="space-y-1.5 text-sm">
              {incoming.map((c, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="min-w-0 flex-1 truncate">{c.label}</span>
                  <span className="font-mono text-[12px] text-status-bad">{relative(c.arrival_at)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </PanelBody>
    </Panel>
  );
}

export function AccountVillages({ villages, commands, roles }: { villages: Village[]; commands: Command[]; roles: Record<number, string> }) {
  const incoming = commands.filter((c) => c.direction === "in");

  return (
    <div className="space-y-4">
      <AccountTotals villages={villages} incoming={incoming.length} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {villages.map((village) => (
          <VillageCard key={village.id} village={village} role={roles[village.id]} incoming={incoming.filter((c) => c.village_coords === village.coords)} />
        ))}
      </div>
    </div>
  );
}
