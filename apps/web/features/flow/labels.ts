import { AGENTS, BUILDINGS, ROLES, UNITS } from "@/lib/game";

export const TOOLS: Record<string, string> = {
  get_village_state: "ler estado da aldeia",
  get_quests: "ler missões",
  lookup_knowledge: "consultar regras do jogo",
  list_barbarians: "listar bárbaras",
  upgrade_building: "construir",
  recruit_units: "recrutar",
  send_farm_attack: "saquear bárbara",
  send_farm_template: "saquear pelo assistente",
  set_farm_templates: "ajustar modelos do assistente de saque",
  read_farm_assistant: "ler assistente de saque",
  send_scavenge: "enviar coleta",
  unlock_scavenge: "desbloquear coleta",
  claim_quest_rewards: "coletar recompensas",
  complete_quest: "concluir missão",
  set_village_goal: "definir objetivo",
  set_village_plan: "definir plano",
  open_daily_bonus: "abrir baú diário",
  accept_friend: "aceitar amizade",
  accept_market_offer: "aceitar oferta no mercado",
  accept_mentor: "aceitar mentor",
  accept_tribe_invite: "aceitar convite de tribo",
  add_friend: "pedir amizade",
  apply_to_tribe: "candidatar-se a tribo",
  assign_flag: "colocar bandeira",
  cancel_market_offer: "cancelar oferta no mercado",
  choose_relic: "escolher relíquia",
  craft_event_item: "forjar item do evento",
  create_market_offer: "criar oferta no mercado",
  equip_relic: "equipar relíquia",
  get_forecast: "prever recursos",
  get_incoming: "ler ataques chegando",
  get_own_offers: "ler ofertas próprias",
  get_target_intel: "ler informações do alvo",
  learn_knight_skill: "aprender habilidade do paladino",
  park_market_offer: "estacionar ferro no mercado",
  plan_scavenge: "planejar coleta",
  read_doc: "ler documentação",
  read_inbox: "ler caixa de entrada",
  read_thread: "ler conversa",
  read_tribe: "ler tribo",
  recruit_knight: "recrutar paladino",
  rename_village: "renomear aldeia",
  reply_forum: "responder no fórum",
  reply_mail: "responder mensagem",
  research_unit: "pesquisar unidade",
  search_docs: "buscar na documentação",
  send_mail: "enviar mensagem",
  send_noble: "enviar nobre",
  send_resources: "enviar recursos",
  send_spy: "enviar exploradores",
  set_profile_text: "escrever texto do perfil",
  simulate_battle: "simular batalha",
  train_knight: "treinar paladino",
  use_item: "usar item",
  browse_game: "passear pelo jogo",
  summary: "resumo",
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

const WORDS: Record<string, string> = { wood: "madeira", clay: "argila", stone: "argila", iron: "ferro", pop: "população" };

export function toolsInText(text: string): string {
  return text.replace(/\b[a-z]+(?:_[a-z]+)+\b/g, (t) => TOOLS[t] ?? t);
}

export function readable(text: string | null | undefined): string {
  if (!text) return "";
  return toolsInText(text)
    .replace(/\b(modo|papel) (growth|defense|offensive|support|expansion|emergency)\b/g, (_, w: string, r: string) => `${w} ${(ROLES[r] ?? r).toLowerCase()}`)
    .replace(/\b(construir|subir|construção de) ([a-z]+)\b/g, (m, v: string, b: string) => (BUILDINGS[b] ? `${v} ${BUILDINGS[b]}` : m))
    .replace(/\b([a-z]+)( →)? nível\b/g, (m, b: string, arrow: string | undefined) => (BUILDINGS[b] ? `${BUILDINGS[b]}${arrow ?? ""} nível` : m))
    .replace(/\b(unidade|recrutar) ([a-z]+)\b/g, (m, v: string, u: string) => (UNITS[u] ? `${v} ${UNITS[u].toLowerCase()}` : m))
    .replace(/\b(wood|clay|stone|iron)\b/g, (w) => WORDS[w] ?? w);
}

export function agentLabel(id: string): string {
  return AGENTS[id] ?? id;
}

export function outcomeLabel(id: string): string {
  return OUTCOMES[id]?.label ?? id;
}
