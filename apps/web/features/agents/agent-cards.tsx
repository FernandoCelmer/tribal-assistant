import { Badge } from "@/components/ui/badge";
import type { Schemas } from "@/lib/api";
import { num, short } from "@/lib/format";
import { AgentMark } from "./agent-mark";
import { AREAS, ORDER, agentLabel } from "./labels";

type Stat = Schemas["AgentStat"];

function rateTone(rate: number): "success" | "warning" | "danger" {
  return rate >= 70 ? "success" : rate >= 40 ? "warning" : "danger";
}

export function AgentCards({ stats, known }: { stats: Stat[]; known: string[] }) {
  const byKey = new Map(stats.map((s) => [s.agent, s]));
  const keys = Array.from(new Set([...known, ...stats.map((s) => s.agent)]));
  keys.sort((a, b) => (ORDER.indexOf(a) === -1 ? 99 : ORDER.indexOf(a)) - (ORDER.indexOf(b) === -1 ? 99 : ORDER.indexOf(b)));

  return (
    <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      {keys.map((key) => {
        const s = byKey.get(key);
        const rate = s && s.actions ? Math.round((s.ok / s.actions) * 100) : null;
        return (
          <li key={key} className="flex min-h-[172px] flex-col rounded-lg border border-border bg-surface p-4">
            <div className="flex items-start gap-3">
              <AgentMark agent={key} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold">{agentLabel(key)}</div>
                <div className="truncate text-[12px] text-secondary">{AREAS[key] ?? key}</div>
              </div>
              {rate == null ? <Badge>sem ações</Badge> : <Badge tone={rateTone(rate)}>{rate}% ok</Badge>}
            </div>
            <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
              {[
                ["feitas", s?.ok ?? 0],
                ["recusadas", s?.refused ?? 0],
                ["falhas", s?.failed ?? 0],
              ].map(([label, value]) => (
                <div key={label} className="rounded-md border border-border-subtle py-2">
                  <dd className="text-lg font-semibold leading-none tabular-nums">{num(value as number)}</dd>
                  <dt className="mt-1 text-[11px] text-muted-foreground">{label}</dt>
                </div>
              ))}
            </dl>
            <p className="mt-auto pt-3 text-[12px] leading-5 text-secondary">
              {s?.last_action ? (
                <>
                  <span className="font-mono text-muted-foreground">{short(s.last_at)}</span> {s.last_action.replaceAll("_", " ")}
                  {s.last_result && <span className="line-clamp-2 text-muted-foreground">{s.last_result}</span>}
                </>
              ) : (
                <span className="text-muted-foreground">ainda não agiu no período</span>
              )}
            </p>
          </li>
        );
      })}
    </ul>
  );
}
