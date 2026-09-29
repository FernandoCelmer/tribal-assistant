import { Ban, Lock, Shield } from "lucide-react";
import { UnitIcon } from "@/components/game/icons";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { num, short } from "@/lib/format";
import { CostLine } from "./cost-line";
import type { Budget, Constraint } from "./types";

const KINDS: Record<string, string> = { defense: "defesa", strategic: "estratégica", operation: "operação", base: "base" };

export function BudgetPanel({ budget, constraints }: { budget?: Budget; constraints?: Constraint[] }) {
  const reservations = budget?.reservations ?? [];
  const vetoes = constraints ?? [];
  return (
    <Panel>
      <PanelHeader title={<><Shield className="size-4 text-secondary" strokeWidth={1.75} />Reservas e vetos</>} aside={<Badge>{reservations.length + vetoes.length}</Badge>} />
      <div className="space-y-3 border-b border-border-subtle p-4">
        <div>
          <div className="text-xs font-medium text-muted-foreground">Livre para gastar</div>
          <CostLine cost={budget?.free} all className="mt-1.5 text-sm" />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <div className="text-xs font-medium text-muted-foreground">Estoque</div>
            <CostLine cost={budget?.stock} all className="mt-1.5 text-secondary" />
          </div>
          <div>
            <div className="text-xs font-medium text-muted-foreground">Reservado</div>
            <CostLine cost={budget?.held} empty="nada reservado" className="mt-1.5 text-secondary" />
          </div>
        </div>
      </div>
      <ul className="divide-y divide-border-subtle">
        {reservations.map((r, i) => (
          <li key={`r-${i}`} className="flex items-start gap-3 px-4 py-3">
            <Lock className="mt-0.5 size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
            <div className="min-w-0 flex-1 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{r.purpose}</span>
                <Badge>{KINDS[r.kind] ?? r.kind}</Badge>
              </div>
              <CostLine cost={r.cost} className="mt-1" />
              {r.troops && Object.keys(r.troops).length > 0 && (
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[13px]">
                  {Object.entries(r.troops).map(([unit, n]) => (
                    <span key={unit} className="inline-flex items-center gap-1.5 tabular-nums"><UnitIcon name={unit} className="size-4" />{num(n)}</span>
                  ))}
                </div>
              )}
              {r.reason && <p className="mt-1 text-[12px] text-muted-foreground">{r.reason}</p>}
            </div>
          </li>
        ))}
        {vetoes.map((c, i) => (
          <li key={`v-${i}`} className="flex items-start gap-3 px-4 py-3">
            <Ban className="mt-0.5 size-4 shrink-0 text-status-bad" strokeWidth={1.75} />
            <div className="min-w-0 flex-1 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="danger">veto</Badge>
                <span>{c.reason}</span>
              </div>
              <div className="mt-1 text-[12px] text-muted-foreground">
                {c.blocks?.length ? `bloqueia ${c.blocks.join(", ")}` : null}
                {c.until ? `${c.blocks?.length ? " · " : ""}até ${short(c.until)}` : null}
              </div>
            </div>
          </li>
        ))}
        {reservations.length === 0 && vetoes.length === 0 && <li className="px-4 py-4 text-[13px] text-secondary">Sem reservas nem vetos ativos.</li>}
      </ul>
    </Panel>
  );
}
