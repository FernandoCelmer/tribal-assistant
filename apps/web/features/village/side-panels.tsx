import { Lock, Pickaxe, Timer } from "lucide-react";
import { UnitIcon } from "@/components/game/icons";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import type { Schemas } from "@/lib/api";
import { num, percent, relative, short, utc } from "@/lib/format";
import { UNITS } from "@/lib/game";

type Order = Schemas["RecruitOrderOut"];
type Scavenge = Schemas["ScavengeOut"];

export function RecruitQueue({ orders }: { orders: Order[] }) {
  return (
    <Panel>
      <PanelHeader title={<><Timer className="size-4 text-secondary" strokeWidth={1.75} />Fila de recrutamento</>} aside={<Badge>{num(orders.length)}</Badge>} />
      <PanelBody>
        {orders.length ? (
          <ul className="divide-y divide-border-subtle">
            {orders.map((o, i) => (
              <li key={`${o.unit}-${i}`} className="flex items-center gap-3 py-2 text-sm first:pt-0 last:pb-0">
                <UnitIcon name={o.unit} />
                <span className="min-w-0 flex-1 truncate"><span className="font-medium tabular-nums">{num(o.count)}</span> {UNITS[o.unit] ?? o.unit}</span>
                <span className="font-mono text-[12px] text-secondary" title={short(o.finishes_at)}>{relative(o.finishes_at)}</span>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-secondary">Nenhum recrutamento em andamento.</p>}
      </PanelBody>
    </Panel>
  );
}

function scavengeState(s: Scavenge, now: number) {
  if (s.is_locked) return s.unlock_at ? <Badge tone="warning">libera {relative(s.unlock_at, now)}</Badge> : <Badge><Lock className="mr-1 size-3" />bloqueada</Badge>;
  if (s.return_at && utc(s.return_at).getTime() > now) return <Badge tone="ok">volta {relative(s.return_at, now)}</Badge>;
  return <Badge tone="success">livre</Badge>;
}

export function ScavengePanel({ options }: { options: Scavenge[] }) {
  const now = Date.now();
  const free = options.filter((s) => !s.is_locked && !(s.return_at && utc(s.return_at).getTime() > now)).length;

  return (
    <Panel>
      <PanelHeader title={<><Pickaxe className="size-4 text-secondary" strokeWidth={1.75} />Coleta</>} aside={options.length ? <Badge>{num(free)} livres</Badge> : undefined} />
      <PanelBody>
        {options.length ? (
          <ul className="divide-y divide-border-subtle">
            {options.map((s) => (
              <li key={s.option_id} className="flex items-center gap-3 py-2 text-sm first:pt-0 last:pb-0">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-md border border-border font-mono text-[11px] text-secondary">{s.option_id}</span>
                <span className="min-w-0 flex-1">
                  <span className={s.is_locked ? "text-secondary" : undefined}>{s.name}</span>
                  <span className="block text-[12px] text-muted-foreground">saque {percent(s.loot_factor)} da capacidade</span>
                </span>
                {scavengeState(s, now)}
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-secondary">Coleta indisponível nesta aldeia.</p>}
      </PanelBody>
    </Panel>
  );
}
