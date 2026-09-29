import { AGENTS } from "@/lib/game";

export const TOOLS: Record<string, string> = {
  get_village_state: "ler estado da aldeia",
  get_quests: "ler missões",
  lookup_knowledge: "consultar regras do jogo",
  list_barbarians: "listar bárbaras",
  upgrade_building: "construir",
  recruit_units: "recrutar",
  send_farm_attack: "saquear bárbara",
  send_scavenge: "enviar coleta",
  unlock_scavenge: "desbloquear coleta",
  claim_quest_rewards: "coletar recompensas",
  complete_quest: "concluir missão",
  set_village_goal: "definir objetivo",
  set_village_plan: "definir plano",
  open_daily_bonus: "abrir baú diário",
  build: "construir",
  recruit: "recrutar",
  attack: "saquear",
  farm: "saquear",
  scavenge: "coleta",
  quest: "missão",
};

export const OUTCOMES: Record<string, { label: string; tone: string; fill: string }> = {
  ok: { label: "feito", tone: "text-status-ok", fill: "bg-status-ok" },
  refused: { label: "recusado pela trava", tone: "text-status-warn", fill: "bg-status-warn" },
  failed: { label: "erro no jogo", tone: "text-status-bad", fill: "bg-status-bad" },
};

export function toolLabel(id: string): string {
  return TOOLS[id] ?? id.replace(/_/g, " ");
}

export function agentLabel(id: string): string {
  return AGENTS[id] ?? id;
}

export function outcomeLabel(id: string): string {
  return OUTCOMES[id]?.label ?? id;
}
