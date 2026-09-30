"use client";

import { Crown } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import { agentLabel, readable } from "@/features/flow/labels";
import type { Item, Status } from "@/features/live/state";
import { actionIcon, agentIcon } from "./icons";

type Edge = { d: string; tone: "idle" | "active" | "chosen" };

const BADGE: Partial<Record<Status, string>> = { running: "Em execução", ok: "Feita", failed: "Falhou", deferred: "Adiada" };
const SHOWN = 7;

export function chosen(items: Item[]): Item | undefined {
  return items.find((i) => i.status === "running") ?? items.find((i) => i.status === "ok") ?? items.find((i) => i.status === "pending") ?? items[0];
}

function building(item: Item): string | undefined {
  const words = item.title.split(" ");
  return item.action === "upgrade_building" ? words[words.length - 1] : undefined;
}

export function FlowGraph({ specialists, items, thinking }: { specialists: { key: string; title: string }[]; items: Item[]; thinking: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState<Edge[]>([]);
  const shown = items.slice(0, SHOWN);
  const pick = chosen(shown);
  const active = new Set(shown.map((i) => i.source));
  const half = Math.ceil(specialists.length / 2);
  const columns = [specialists.slice(0, half), specialists.slice(half)];

  useLayoutEffect(() => {
    const root = box.current;
    if (!root) return;

    const draw = () => {
      const base = root.getBoundingClientRect();
      const at = (el: Element) => {
        const r = el.getBoundingClientRect();
        return { left: r.left - base.left, right: r.right - base.left, top: r.top - base.top, bottom: r.bottom - base.top, mid: r.top - base.top + r.height / 2 };
      };
      const hub = root.querySelector("[data-hub]");
      if (!hub) return;
      const h = at(hub);
      const lane = root.querySelector("[data-lane]");
      const laneRight = lane ? at(lane).right + 14 : h.left - 60;
      const next: Edge[] = [];

      root.querySelectorAll<HTMLElement>("[data-agent]").forEach((node) => {
        const n = at(node);
        const column = node.dataset.column;
        const tone = node.dataset.on ? "active" : "idle";
        const endX = h.left + 2;
        const endY = h.mid;
        if (column === "0") {
          const d = `M${n.right},${n.mid} L${laneRight},${n.mid} C${(laneRight + endX) / 2},${n.mid} ${(laneRight + endX) / 2},${endY} ${endX},${endY}`;
          next.push({ d, tone });
        } else {
          const mid = (n.right + endX) / 2;
          next.push({ d: `M${n.right},${n.mid} C${mid},${n.mid} ${mid},${endY} ${endX},${endY}`, tone });
        }
      });

      root.querySelectorAll<HTMLElement>("[data-proposal]").forEach((node) => {
        const n = at(node);
        const startX = h.right - 2;
        const mid = (startX + n.left) / 2;
        next.push({ d: `M${startX},${h.mid} C${mid},${h.mid} ${mid},${n.mid} ${n.left - 4},${n.mid}`, tone: node.dataset.chosen ? "chosen" : node.dataset.done ? "active" : "idle" });
      });

      setEdges(next.sort((a, b) => ["idle", "active", "chosen"].indexOf(a.tone) - ["idle", "active", "chosen"].indexOf(b.tone)));
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(root);
    return () => observer.disconnect();
  }, [specialists, shown.map((i) => `${i.key}:${i.status}`).join("|"), active.size]);

  return (
    <div className="tw-graph" ref={box}>
      <svg className="tw-edges" aria-hidden>
        <defs>
          {(["idle", "active", "chosen"] as const).map((tone) => (
            <marker key={tone} id={`tw-arrow-${tone}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L8,4 L0,8 z" className={`tw-arrow-${tone}`} />
            </marker>
          ))}
        </defs>
        {edges.map((edge, i) => (
          <path key={i} d={edge.d} className={`tw-edge tw-edge-${edge.tone}`} markerEnd={`url(#tw-arrow-${edge.tone})`} />
        ))}
      </svg>

      <div className="tw-agents">
        {columns.map((column, c) => (
          <div key={c} className="tw-agent-column" data-lane={c === 1 ? "" : undefined} data-offset={c === 1 ? "" : undefined}>
            {column.map((s) => {
              const Icon = agentIcon(s.key);
              const on = active.has(s.key) || thinking;
              return (
                <div key={s.key} className="tw-node" data-agent data-column={c} data-on={on || undefined}>
                  <Icon size={16} />
                  <span className="tw-node-name">{agentLabel(s.key) || s.title}</span>
                  <span className="tw-dot" />
                </div>
              );
            })}
          </div>
        ))}
      </div>

      <div className="tw-hub" data-hub>
        <Crown size={26} />
        <strong>Coordenador</strong>
        <span>{items.length ? `${items.length} proposta${items.length === 1 ? "" : "s"}` : thinking ? "reunindo…" : "sem propostas"}</span>
      </div>

      <div className="tw-proposals">
        {shown.map((item) => {
          const Icon = actionIcon(item.action, building(item));
          const isChosen = pick?.key === item.key;
          return (
            <div key={item.key} className="tw-node tw-proposal" data-proposal data-chosen={isChosen || undefined} data-done={item.status === "ok" || undefined} data-status={item.status}>
              <Icon size={16} />
              <span className="tw-node-name">{readable(item.title)}</span>
              {BADGE[item.status] && <span className="tw-badge" data-status={item.status}>{BADGE[item.status]}</span>}
            </div>
          );
        })}
        {!shown.length && <div className="tw-empty">aguardando a próxima rodada</div>}
      </div>
    </div>
  );
}
