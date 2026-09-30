import { toolLabel } from "@/features/flow/labels";
import { AGENTS } from "@/lib/game";

export const KIND_LABELS: Record<string, string> = {
  prompt: "contexto enviado",
  thought: "raciocínio",
  tool_call: "chamou",
  tool_result: "resposta",
  plan: "plano",
  summary: "resumo",
  info: "info",
  error: "erro",
};

export const TRIGGERS: Record<string, string> = { schedule: "agendada", dashboard: "painel", web: "painel", cli: "terminal", mcp: "MCP", manual: "manual", api: "API" };

export const AREAS: Record<string, string> = {
  quartermaster: "missões e recompensas",
  strategist: "objetivo da aldeia",
  steward: "relíquia, bandeira, paladino, itens e forja",
  economy: "armazém, fazenda, reservas e mercado",
  infrastructure: "próxima obra e gargalo",
  recruitment: "tropas e produção de unidades",
  defense: "ataques chegando, vetos e reservas",
  attack: "saques e coleta",
  expansion: "caminho do nobre",
  conquest: "conquista de aldeias com nobre",
  logistics: "envio de recursos entre aldeias",
  free_finish: "termina obras curtas de graça",
  intelligence: "relatórios, vizinhos e desafios",
  diplomacy: "tribo e mentor",
  social: "mensagens, amigos, fórum da tribo e contatos",
  coordinator: "compara propostas e decide",
  operator: "ordens diretas (MCP)",
  economist: "substituído por Economia e Infraestrutura",
  commander: "substituído por Recrutamento",
  raider: "substituído por Ataque",
};

export const ORDER = Object.keys(AREAS);

export function stepLabel(step: string | null | undefined): string {
  if (!step) return "";
  const [kind, ...rest] = step.split(" ");
  if (!KIND_LABELS[kind]) return step;
  return [KIND_LABELS[kind], ...rest.map((t) => (/^[a-z]+(_[a-z]+)+$/.test(t) ? toolLabel(t) : t))].join(" ");
}

export function agentLabel(key: string | null | undefined): string {
  if (!key) return "—";
  return AGENTS[key] ?? key;
}

export const RUN_STATUS: Record<string, { label: string; tone: "neutral" | "success" | "warning" | "danger" }> = {
  running: { label: "rodando", tone: "warning" },
  done: { label: "ok", tone: "success" },
  failed: { label: "falhou", tone: "danger" },
  skipped: { label: "pulada", tone: "neutral" },
  interrupted: { label: "interrompida", tone: "warning" },
};

export function runStatus(status: string) {
  return RUN_STATUS[status] ?? { label: status, tone: "neutral" as const };
}

export function brainLabel(run: { brain: string; model?: string | null; provider?: string | null }): string {
  return run.brain === "llm" ? run.model || run.provider || "IA" : "regras";
}

export function refused(step: { kind: string; content: string }): boolean {
  return step.kind === "tool_result" && step.content.startsWith("RECUSADO");
}
