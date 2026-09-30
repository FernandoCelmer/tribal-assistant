import type { Schemas } from "@/lib/api";
import { purposeLabel, type Budget, type Entry } from "@/features/strategy/types";

export { purposeLabel };
import { agentLabel } from "./labels";

type Round = Schemas["CoordinationOut"];
type Flow = Schemas["FlowOut"];

export type Deferral = { label: string; group: string; plain: string };

export const DEFERRALS: Record<string, Deferral> = {
  resources: { label: "falta recurso", group: "resources", plain: "ainda não há recurso suficiente no armazém" },
  population: { label: "falta população", group: "resources", plain: "a fazenda não comporta mais nada" },
  reserved: { label: "recurso reservado", group: "reserved", plain: "o recurso existe, mas está guardado para outra finalidade" },
  veto: { label: "vetado", group: "veto", plain: "uma trava de segurança proibiu esta ação agora" },
  troops: { label: "tropas ocupadas", group: "veto", plain: "as tropas necessárias estão fora de casa ou comprometidas" },
  queue: { label: "fila cheia", group: "queue", plain: "a fila de construção já está ocupada" },
  limit: { label: "limite da rodada", group: "limit", plain: "a rodada já fez o máximo de ações permitido" },
  recent: { label: "feito há pouco", group: "recent", plain: "a mesma ação saiu há pouco; espera o jogo confirmar" },
  dependency: { label: "depende de outra ação", group: "other", plain: "precisa que outra ação aconteça antes" },
  learned: { label: "recusado antes", group: "other", plain: "o jogo recusou isso antes e o agente aprendeu a esperar" },
};

export const GROUPS: { id: string; label: string; tone: string }[] = [
  { id: "resources", label: "sem recurso", tone: "text-neutral-200" },
  { id: "reserved", label: "reserva", tone: "text-neutral-400" },
  { id: "recent", label: "feito há pouco", tone: "text-neutral-600" },
  { id: "queue", label: "fila cheia", tone: "text-neutral-300" },
  { id: "limit", label: "limite de ações", tone: "text-neutral-500" },
  { id: "veto", label: "veto ou tropas", tone: "text-neutral-100" },
  { id: "other", label: "dependência ou aprendizado", tone: "text-neutral-700" },
];

export const RESULTS: Record<string, { label: string; tone: string }> = {
  ok: { label: "feito", tone: "text-status-ok" },
  refused: { label: "recusado pela trava", tone: "text-status-warn" },
  failed: { label: "erro no jogo", tone: "text-status-bad" },
  later: { label: "fica para depois", tone: "text-neutral-500" },
};

export type Explained = Entry & { why_kind?: string; outcome?: string };

export function deferral(kind: string | undefined): Deferral {
  return DEFERRALS[kind ?? ""] ?? DEFERRALS.learned;
}

export function groupOf(kind: string | undefined): (typeof GROUPS)[number] {
  const id = deferral(kind).group;
  return GROUPS.find((g) => g.id === id) ?? GROUPS[GROUPS.length - 1];
}

export function entries(round: Round): { executed: Explained[]; deferred: Explained[]; budget?: Budget } {
  const data = round.data as { executed?: Explained[]; deferred?: Explained[]; budget?: Budget };
  return { executed: data.executed ?? [], deferred: data.deferred ?? [], budget: data.budget };
}

const EXECUTED = "executed";

export function middleLabel(id: string): string {
  if (id === EXECUTED) return "executada";
  return `adiada: ${GROUPS.find((g) => g.id === id)?.label ?? id}`;
}

export function middleTone(id: string): string {
  if (id === EXECUTED) return "text-neutral-300";
  return GROUPS.find((g) => g.id === id)?.tone ?? "text-neutral-600";
}

export function decisionFlow(rounds: Round[]): Flow {
  const left = new Map<string, number>();
  const middle = new Map<string, number>();
  const right = new Map<string, number>();
  const a = new Map<string, number>();
  const b = new Map<string, number>();
  const add = (map: Map<string, number>, key: string) => map.set(key, (map.get(key) ?? 0) + 1);

  for (const round of rounds) {
    const { executed, deferred } = entries(round);
    for (const e of executed) {
      const source = e.source ?? "coordinator";
      const result = e.outcome ?? (e.ok ? "ok" : "failed");
      add(left, source);
      add(middle, EXECUTED);
      add(right, result);
      add(a, `${source}\u0000${EXECUTED}`);
      add(b, `${EXECUTED}\u0000${result}`);
    }
    for (const e of deferred) {
      const source = e.source ?? "coordinator";
      const group = groupOf(e.why_kind).id;
      add(left, source);
      add(middle, group);
      add(right, "later");
      add(a, `${source}\u0000${group}`);
      add(b, `${group}\u0000later`);
    }
  }

  const nodes = (map: Map<string, number>, order?: string[]) =>
    [...map.entries()]
      .map(([id, count]) => ({ id, count }))
      .sort((x, y) => (order ? order.indexOf(x.id) - order.indexOf(y.id) : y.count - x.count));
  const links = (map: Map<string, number>) =>
    [...map.entries()].map(([key, count]) => {
      const [source, target] = key.split("\u0000");
      return { source, target, count };
    });
  const total = [...left.values()].reduce((s, n) => s + n, 0);

  return {
    calls: total,
    runs: rounds.length,
    agents: nodes(left),
    tools: nodes(middle, [EXECUTED, ...GROUPS.map((g) => g.id)]),
    outcomes: nodes(right, Object.keys(RESULTS)),
    agent_tool: links(a),
    tool_outcome: links(b),
  };
}

export const FLOW_TEXT = {
  left: (id: string) => agentLabel(id),
  middle: middleLabel,
  right: (id: string) => RESULTS[id]?.label ?? id,
  middleTone,
  rightTone: (id: string) => RESULTS[id]?.tone,
  units: ["propostas", "propostas"] as [string, string],
  aria: "Propostas de cada especialista, o que o coordenador decidiu e o resultado",
  empty: "Nenhuma proposta registrada nesta rodada.",
  maxUnit: 26,
};
