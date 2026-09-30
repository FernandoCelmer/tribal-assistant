import { Brain, Shuffle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { agentLabel } from "@/features/agents/labels";
import { readable } from "@/features/flow/labels";
import { percent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Exploration, Learned } from "./types";

function BonusBar({ name, value }: { name: string; value: number }) {
  const delta = value - 1;
  const width = Math.min(50, Math.abs(delta) * 50);
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)_3.5rem] items-center gap-3 text-[13px]">
      <span className="truncate text-secondary">{agentLabel(name)}</span>
      <span className="relative h-2 rounded-full bg-surface-hover">
        <span aria-hidden className="absolute inset-y-0 left-1/2 w-px bg-border-hover" />
        <span className={cn("absolute inset-y-0 rounded-full", delta >= 0 ? "left-1/2 bg-status-ok" : "right-1/2 bg-status-warn")} style={{ width: `${width}%` }} />
      </span>
      <span className="text-right font-mono tabular-nums">{value.toFixed(2)}×</span>
    </li>
  );
}

export function LearningPanel({ learned, exploration }: { learned?: Learned | null; exploration?: Exploration | null }) {
  const bonus = Object.entries(learned?.bonus ?? {}).sort((a, b) => b[1] - a[1]);
  return (
    <Panel>
      <PanelHeader
        title={<><Brain className="size-4 text-secondary" strokeWidth={1.75} />Aprendizado</>}
        description="quanto cada especialista pesa depois de medir o que rendeu, e quando a rodada experimenta outra opção"
        aside={<Badge tone={learned?.repeated ? "warning" : "neutral"}>explora {percent(learned?.explore_rate ?? 0)}</Badge>}
      />
      <div className="space-y-4 p-4">
        {exploration ? (
          <div className="rounded-md border border-border-subtle p-3 text-[13px]">
            <div className="flex items-center gap-2 font-medium"><Shuffle className="size-3.5" strokeWidth={1.75} />Esta rodada explorou</div>
            <p className="mt-1 text-secondary">{readable(exploration.title ?? "")}{exploration.instead_of ? ` no lugar de ${readable(exploration.instead_of)}` : ""}</p>
            {exploration.reason && <p className="mt-1 text-muted-foreground">{readable(exploration.reason)}</p>}
          </div>
        ) : (
          <p className="text-[13px] text-secondary">
            {learned?.repeated ? `Rodadas repetidas há ${learned.streak ?? 0} vezes: a chance de explorar sobe.` : "Esta rodada seguiu a prioridade normal."}
          </p>
        )}
        {bonus.length > 0 ? (
          <ul className="space-y-2">{bonus.map(([name, value]) => <BonusBar key={name} name={name} value={value} />)}</ul>
        ) : (
          <p className="text-[13px] text-muted-foreground">Ainda sem resultados medidos para ajustar os pesos.</p>
        )}
      </div>
    </Panel>
  );
}
