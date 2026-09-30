"""Every tunable number the agents decide with: default, meaning and the rule that moves it."""

from dataclasses import fields

from tribal_assistant.core.agents.coordination.strategy import WEIGHTS, Weights
from tribal_assistant.core.agents.knob_rules import (
    KnobSpec,
    cooldown,
    cooldowns,
    either,
    less_when,
    more_when,
    settle,
)

ROLE_LIMITS = {
    "growth": (0.1, 0.3, 12, 12, 30),
    "expansion": (0.1, 0.3, 12, 12, 30),
    "defense": (0.1, 0.8, 4, 8, 60),
    "support": (0.1, 0.7, 6, 10, 45),
    "offensive": (0.05, 0.7, 30, 15, 20),
}
EMERGENCY_RECRUIT_BUDGET = 0.9
POLICY_FIELDS = ("resource_reserve", "recruit_budget", "max_attacks_per_hour", "attack_radius", "retarget_minutes")

STOCK_EMPTY = more_when("stock_empty", 0.3, "estoque quase zerado")
STARVED = less_when("recruit_starved", 0.3, "recrutamento sem recurso")
STORAGE_FULL_UP = more_when("storage_full", 0.2, "armazém cheio")
STORAGE_FULL_DOWN = less_when("storage_full", 0.2, "armazém cheio")
STORAGE_CALM = settle("storage_full", 0.05, "armazém cheio")
POP_LOCKED_UP = either(more_when("pop_locked", 0.2, "população travada"), settle("pop_locked", 0.05, "população travada"))
RAIDS_LOST_DOWN = less_when("raids_lost", 0.3, "saques perdendo tropas")
RAIDS_LOST_UP = more_when("raids_lost", 0.3, "saques perdendo tropas")
RAIDS_CALM = settle("raids_lost", 0.1, "saques perdendo tropas")
NO_TARGETS_UP = more_when("no_targets", 0.3, "nenhuma bárbara no alcance")
THREAT_UP = either(more_when("threatened", 0.1, "ataques chegando"), settle("threatened", 0.01, "ataques chegando"))
IDLE_QUEUE_UP = more_when("idle_queue", 0.3, "fila de obras parada")
IRON_CALM = settle("iron_short", 0.1, "obras esperando ferro")
IRON_SHORT_UP = more_when("iron_short", 0.3, "obras esperando ferro")
IRON_SHORT_DOWN = less_when("iron_short", 0.3, "obras esperando ferro")
STORAGE_UP_OR_CALM = either(STORAGE_FULL_UP, STORAGE_CALM)
STORAGE_DOWN_OR_CALM = either(STORAGE_FULL_DOWN, STORAGE_CALM)
NOBLES_FAILED_UP = either(more_when("nobles_failed", 0.3, "nobres falhando"), settle("nobles_failed", 0.05, "nobres falhando"))
SHIPMENTS_FAILED_UP = either(more_when("shipments_failed", 0.3, "envios entre aldeias falhando"), settle("shipments_failed", 0.05, "envios entre aldeias falhando"))


def _policy() -> dict[str, KnobSpec]:
    rules = {
        "resource_reserve": (either(STOCK_EMPTY, STARVED), True, False, "fração do armazém reservada"),
        "recruit_budget": (either(less_when("idle_queue", 0.3, "fila de obras parada"), STORAGE_FULL_UP), True, False, "fração da sobra que o recrutamento pode gastar"),
        "max_attacks_per_hour": (either(RAIDS_LOST_DOWN, more_when("raids_capped", 0.3, "saques barrados pelo limite por hora")), False, True, "ataques e sondas por hora"),
        "attack_radius": (either(RAIDS_LOST_DOWN, NO_TARGETS_UP), False, True, "raio máximo de saque em campos"),
        "retarget_minutes": (either(RAIDS_LOST_UP, less_when("no_targets", 0.3, "poucos alvos: voltar antes")), False, True, "minutos antes de atacar o mesmo alvo de novo"),
    }
    specs = {}
    for role, values in ROLE_LIMITS.items():
        for name, default in zip(POLICY_FIELDS, values, strict=True):
            rule, share, integer, text = rules[name]
            specs[f"policy.{role}.{name}"] = KnobSpec(default, f"{text} no papel {role}", rule, share=share, integer=integer)
    specs["policy.emergency.recruit_budget"] = KnobSpec(EMERGENCY_RECRUIT_BUDGET, "fração da sobra que o recrutamento pode gastar em emergência", rules["recruit_budget"][0], share=True)
    return specs


def _weights() -> dict[str, KnobSpec]:
    specs = {}
    for role, weights in WEIGHTS.items():
        for item in fields(Weights):
            specs[f"weight.{role.value}.{item.name}"] = KnobSpec(getattr(weights, item.name), f"peso de {item.name} na prioridade do papel {role.value}", share=True)
    return specs


CATALOG: dict[str, KnobSpec] = {
    "base_stock_share": KnobSpec(0.25, "fração do estoque que a reserva mínima pode segurar", either(STOCK_EMPTY, STARVED), share=True),
    "filler_wait_hours": KnobSpec(0.75, "espera da próxima obra do plano antes de encaixar uma obra que já cabe", either(less_when("idle_queue", 0.3, "fila de obras parada"), settle("idle_queue", 0.05, "fila de obras parada"))),
    "scavenge_share": KnobSpec(
        0.4,
        "fração da população máxima em lanceiros para a coleta",
        either(less_when("pop_locked", 0.2, "população travada"), more_when("scavenge_idle", 0.3, "coleta sem tropas")),
        share=True,
    ),
    **_policy(),
    "storage.near_full_share": KnobSpec(0.85, "armazém considerado quase cheio (gatilho do excedente em tropas)", either(STORAGE_FULL_DOWN, STOCK_EMPTY), share=True),
    "recruit.near_full_budget": KnobSpec(0.8, "fração da sobra liberada ao recrutamento com armazém quase cheio", either(STORAGE_FULL_UP, less_when("stock_empty", 0.3, "estoque quase zerado")), share=True),
    "recruit.batch": KnobSpec(25, "lote de recrutamento", either(STORAGE_FULL_UP, STARVED), integer=True),
    "recruit.min_batch": KnobSpec(5, "menor lote que vale recrutar", either(STARVED, settle("recruit_starved", 0.1, "recrutamento sem recurso")), integer=True),
    "scavenge.cap": KnobSpec(1000, "teto de lanceiros para a coleta", either(more_when("scavenge_idle", 0.3, "coleta sem tropas"), less_when("pop_locked", 0.2, "população travada")), integer=True),
    "spy.min": KnobSpec(5, "exploradores mínimos para sondar", integer=True),
    "spy.per_light": KnobSpec(5, "cavalarias leves por explorador mantido", integer=True),
    "plan_reserve.idle_hours": KnobSpec(0.25, "horas até a próxima obra para reservar com a fila parada", either(IDLE_QUEUE_UP, STARVED)),
    "plan_reserve.busy_hours": KnobSpec(1.5, "horas até a próxima obra para reservar com a fila andando", either(IDLE_QUEUE_UP, STARVED)),
    "storage.horizon_hours": KnobSpec(3.0, "horas mínimas de folga do armazém antes de subi-lo", either(STORAGE_FULL_UP, less_when("stock_empty", 0.3, "estoque quase zerado"))),
    "storage.queue_margin_hours": KnobSpec(2.0, "horas somadas à fila para decidir o armazém", STORAGE_UP_OR_CALM),
    "farm.free_share": KnobSpec(0.15, "fração de população livre que chama a fazenda", either(POP_LOCKED_UP, less_when("stock_empty", 0.3, "estoque quase zerado")), share=True),
    "farm.lead_hours": KnobSpec(1.0, "folga em horas entre travar a população e a fazenda ficar pronta", POP_LOCKED_UP),
    "economy.pop_window_hours": KnobSpec(6, "janela em horas para medir o ritmo da população"),
    "capacity.storage_hours": KnobSpec(24, "armazém do plano só vale se encher dentro destas horas", STORAGE_UP_OR_CALM),
    "capacity.farm_free_share": KnobSpec(0.3, "fazenda do plano só vale com população livre abaixo desta fração", POP_LOCKED_UP, share=True),
    "market.min_gap": KnobSpec(200, "diferença mínima entre recursos para negociar", either(less_when("storage_full", 0.3, "armazém cheio"), STOCK_EMPTY), integer=True),
    "market.max_minutes": KnobSpec(360, "viagem máxima de uma oferta aceita em minutos", integer=True),
    "market.offer_hours": KnobSpec(5, "validade da oferta própria em horas", integer=True),
    "market.park_memory_hours": KnobSpec(96, "horas que o ferro estacionado fica lembrado", integer=True),
    "iron_parking.full_share": KnobSpec(0.85, "ferro nesta fração do armazém vai para o mercado", STORAGE_DOWN_OR_CALM, share=True),
    "iron_parking.soon_hours": KnobSpec(2.0, "estacionar ferro quando encher dentro destas horas", STORAGE_UP_OR_CALM),
    "iron_parking.keep_share": KnobSpec(0.25, "fração do armazém de ferro mantida em casa", either(IRON_SHORT_UP, STORAGE_FULL_DOWN), share=True),
    "iron_parking.floor_share": KnobSpec(0.2, "fração mínima do armazém que fica em casa ao estacionar", either(IRON_SHORT_UP, IRON_CALM), share=True),
    "iron_parking.min_lot": KnobSpec(500, "menor oferta de ferro estacionado", STORAGE_DOWN_OR_CALM, integer=True),
    "iron_parking.threat_hours": KnobSpec(6.0, "ataque dentro destas horas estaciona o ferro"),
    "iron_parking.offer_hours": KnobSpec(1, "validade da oferta de ferro estacionado em horas", integer=True),
    "cooldown.market": KnobSpec(0.5, "horas entre buscas de ofertas no mercado", cooldown("accept_market_offer")),
    "cooldown.market_offer": KnobSpec(1, "horas entre ofertas próprias", cooldown("create_market_offer")),
    "cooldown.market_park": KnobSpec(2, "horas entre estacionamentos de ferro", cooldown("park_market_offer")),
    "cooldown.market_release": KnobSpec(0.5, "horas entre resgates de ferro estacionado", cooldown("cancel_market_offer")),
    "cooldown.forge": KnobSpec(3, "horas entre visitas à forja do evento", cooldown("craft_event_item")),
    "cooldown.relic": KnobSpec(6, "horas entre verificações de relíquia", cooldowns("choose_relic", "equip_relic")),
    "cooldown.flag": KnobSpec(6, "horas entre verificações de bandeira", cooldown("assign_flag")),
    "cooldown.knight": KnobSpec(1, "horas entre verificações do paladino", cooldowns("recruit_knight", "learn_knight_skill", "train_knight")),
    "cooldown.items": KnobSpec(0.5, "horas entre leituras do inventário", cooldown("use_item")),
    "cooldown.rename": KnobSpec(24, "horas entre tentativas de renomear para a missão", cooldown("rename_village")),
    "cooldown.tribe": KnobSpec(12, "horas entre buscas de tribo", cooldowns("apply_to_tribe", "accept_tribe_invite")),
    "cooldown.mentor": KnobSpec(24, "horas entre buscas de mentor", cooldown("accept_mentor")),
    "cooldown.smith": KnobSpec(1, "horas entre visitas ao ferreiro", cooldown("research_unit")),
    "cooldown.daily_bonus": KnobSpec(4, "horas entre aberturas do bônus diário", cooldown("open_daily_bonus")),
    "diplomacy.apply_retry_hours": KnobSpec(48, "horas antes de pedir de novo à mesma tribo"),
    "pacing.main_early_cap": KnobSpec(10, "edifício principal antes do portão do estábulo", integer=True),
    "pacing.iron_gap": KnobSpec(3, "níveis que a mina de ferro fica abaixo até o estábulo", either(IRON_SHORT_DOWN, IRON_CALM), integer=True),
    "raid.min_confidence": KnobSpec(0.35, "confiança mínima para saquear", either(RAIDS_LOST_UP, less_when("raids_vetoed", 0.5, "saques vetados demais")), share=True),
    "raid.listing": KnobSpec(30, "bárbaras avaliadas por rodada", integer=True),
    "raid.max_probes": KnobSpec(3, "sondas por rodada", integer=True),
    "raid.intel_half_life_hours": KnobSpec(24, "meia-vida da confiança num relatório"),
    "raid.max_base": KnobSpec(3, "saques por rodada sem cavalaria leve", integer=True),
    "raid.max_cap": KnobSpec(12, "teto de saques por rodada", either(more_when("raids_capped", 0.3, "saques barrados pelo limite"), settle("raids_capped", 0.1, "saques barrados pelo limite")), integer=True),
    "raid.light_per_raid": KnobSpec(20, "cavalarias leves que liberam mais um saque por rodada", integer=True),
    "raid.radius_infantry": KnobSpec(4, "raio seguro da infantaria em campos", either(RAIDS_LOST_DOWN, NO_TARGETS_UP), integer=True),
    "raid.radius_cavalry": KnobSpec(10, "raio seguro da cavalaria em campos", either(RAIDS_LOST_DOWN, NO_TARGETS_UP), integer=True),
    "raid.min_infantry": KnobSpec(10, "menor grupo de infantaria enviado sozinho", either(RAIDS_LOST_UP, RAIDS_CALM), integer=True),
    "raid.paladin_points": KnobSpec(100, "pontos máximos de bárbara desconhecida para o paladino", either(RAIDS_LOST_DOWN, RAIDS_CALM), integer=True),
    "raid.unknown_haul": KnobSpec(300, "saque suposto de uma bárbara sem histórico", integer=True),
    "raid.history_margin": KnobSpec(1.15, "folga de carga sobre o saque médio"),
    "raid.wall_light_factor": KnobSpec(1.0, "multiplicador da cavalaria leve pela muralha", either(RAIDS_LOST_UP, RAIDS_CALM)),
    "raid.ram_wall": KnobSpec(3, "muralha a partir da qual só com aríetes", integer=True),
    "defense.prepare_hours": KnobSpec(72, "horas antes do fim da proteção para preparar a defesa", THREAT_UP),
    "defense.wall_target": KnobSpec(8, "muralha da preparação", THREAT_UP, integer=True),
    "defense.spear_target": KnobSpec(80, "lanceiros da preparação", THREAT_UP, integer=True),
    "defense.sword_target": KnobSpec(80, "espadachins da preparação", THREAT_UP, integer=True),
    "defense.spy_home": KnobSpec(5, "exploradores em casa contra espionagem", integer=True),
    "defense.watchtower_target": KnobSpec(1, "torre de vigia no papel defesa", integer=True),
    "defense.batch": KnobSpec(20, "lote de defensores", THREAT_UP, integer=True),
    "defense.hide_share_danger": KnobSpec(0.3, "fração do armazém escondida com vizinho perigoso", share=True),
    "defense.hide_share_near": KnobSpec(0.2, "fração do armazém escondida com vizinhos por perto", share=True),
    "defense.hide_share_calm": KnobSpec(0.1, "fração do armazém escondida sem vizinhos", share=True),
    "dodge.radius": KnobSpec(20, "raio da esquiva em campos", either(more_when("dodge_stuck", 0.2, "esquiva sem bárbara no raio"), settle("dodge_stuck", 0.01, "esquiva sem bárbara no raio")), integer=True),
    "dodge.max_losses": KnobSpec(0.5, "perda máxima do atacante para considerar a esquiva", share=True),
    "dodge.margin_minutes": KnobSpec(10, "minutos de folga das tropas fora no impacto", integer=True),
    "dodge.min_pop": KnobSpec(10, "população mínima em casa para esquivar", integer=True),
    "threat.radius": KnobSpec(8, "raio de busca de jogadores vizinhos", integer=True),
    "threat.danger_distance": KnobSpec(5.0, "distância de um vizinho perigoso"),
    "threat.danger_ratio": KnobSpec(2.0, "vezes os nossos pontos para um vizinho ser perigoso"),
    "threat.danger_points": KnobSpec(300, "pontos mínimos de um vizinho perigoso", integer=True),
    "noble.min_farm": KnobSpec(24, "fazenda mínima para o nobre", integer=True),
    "noble.min_army_pop": KnobSpec(2000, "exército mínimo em população para o nobre", integer=True),
    "expansion.reserve_share": KnobSpec(0.3, "fração do estoque guardada para academia e nobre", either(STARVED, STORAGE_FULL_UP), share=True),
    "expansion.target_radius": KnobSpec(10, "raio da bárbara alvo do nobre", integer=True),
    "role.expansion_progress": KnobSpec(0.8, "progresso da academia que muda para expansão", share=True),
    "role.offensive_light": KnobSpec(20, "cavalarias leves que liberam o papel ofensivo", integer=True),
    "role.offensive_targets": KnobSpec(3, "alvos bons que liberam o papel ofensivo", integer=True),
    "role.confirm_rounds": KnobSpec(3, "rodadas pedindo o mesmo papel antes de trocar", integer=True),
    "learning.repeat_window_minutes": KnobSpec(20, "janela das falhas repetidas em minutos", integer=True),
    "learning.repeat_limit": KnobSpec(2, "falhas iguais antes de bloquear a ação", integer=True),
    "coordinator.max_actions": KnobSpec(10, "ações por rodada", either(more_when("actions_capped", 0.3, "rodadas no limite de ações"), settle("actions_capped", 0.05, "rodadas no limite de ações")), integer=True),
    "coordinator.recent_minutes": KnobSpec(10, "minutos em que uma ação feita espera o jogo confirmar", integer=True),
    **_weights(),
    "intel.stale_hours": KnobSpec(24, "horas para um relatório virar velho"),
    "knight.train_stock_multiple": KnobSpec(4, "vezes o custo do treino que o menor recurso precisa ter", STORAGE_DOWN_OR_CALM),
    "knight.train_full_share": KnobSpec(0.8, "armazém cheio a partir desta fração libera o treino", STORAGE_DOWN_OR_CALM, share=True),
    "items.unit_bonus_min": KnobSpec(20, "tropas em casa para usar um bônus de unidade", integer=True),
    "items.pack_min_storage": KnobSpec(4000, "armazém mínimo para abrir pacote de recursos", integer=True),
    "quest.wall_cap": KnobSpec(3, "maior muralha que uma missão pode pedir", integer=True),
    "quest.hide_cap": KnobSpec(3, "maior esconderijo que uma missão pode pedir", integer=True),
    "plan.storage_fill_share": KnobSpec(0.6, "estoque nesta fração do armazém põe o armazém no plano", STORAGE_DOWN_OR_CALM, share=True),
    "plan.storage_min_hours": KnobSpec(6, "armazém que enche antes destas horas entra no plano", STORAGE_UP_OR_CALM),
    "plan.light_min": KnobSpec(10, "cavalaria leve mínima pedida pelo plano automático", integer=True),
    "plan.light_step": KnobSpec(5, "cavalarias leves a mais por plano automático", integer=True),
    "plan.farm_min_free": KnobSpec(20, "população livre mínima antes da fazenda no plano", POP_LOCKED_UP, integer=True),
    "logistics.keep_share": KnobSpec(0.3, "fração do armazém que a aldeia de origem nunca envia", either(STOCK_EMPTY, STORAGE_FULL_DOWN), share=True),
    "logistics.surplus_share": KnobSpec(0.6, "estoque nesta fração do armazém torna a aldeia doadora", STORAGE_DOWN_OR_CALM, share=True),
    "logistics.full_hours": KnobSpec(4.0, "armazém que enche antes destas horas libera o envio", STORAGE_UP_OR_CALM),
    "logistics.min_lot": KnobSpec(1000, "menor envio entre aldeias próprias", either(STORAGE_FULL_DOWN, SHIPMENTS_FAILED_UP), integer=True),
    "logistics.dest_hours": KnobSpec(2.0, "horas entre envios para a mesma aldeia", cooldown("send_resources")),
    "logistics.stall_hours": KnobSpec(1.0, "horas de espera por recurso que tornam a aldeia travada", either(less_when("idle_queue", 0.3, "fila de obras parada"), settle("idle_queue", 0.05, "fila de obras parada"))),
    "logistics.dest_fill_share": KnobSpec(0.9, "fração do armazém de destino que um envio pode encher", share=True),
    "conquest.escort_pop": KnobSpec(200, "população mínima de escolta por nobre", NOBLES_FAILED_UP, integer=True),
    "conquest.cleanup_pop": KnobSpec(500, "população ofensiva mínima da limpeza antes do nobre", NOBLES_FAILED_UP, integer=True),
    "conquest.cleanup_share": KnobSpec(0.8, "fração da tropa ofensiva em casa enviada na limpeza", share=True),
    "conquest.train_max": KnobSpec(5, "nobres no mesmo trem", integer=True),
    "conquest.scout_hours": KnobSpec(12, "horas em que a espionagem do alvo vale para a conquista"),
    "conquest.clean_hours": KnobSpec(3, "horas em que a limpeza vale antes do nobre"),
    "conquest.loyalty_hit": KnobSpec(20, "lealdade que um nobre tira no pior caso", integer=True),
    "conquest.noble_gap_minutes": KnobSpec(30, "minutos entre ataques com nobre no mesmo alvo", NOBLES_FAILED_UP, integer=True),
    "account.exposed_distance": KnobSpec(8.0, "jogador mais perto que isto torna a aldeia a exposta da conta", THREAT_UP),
    "account.offensive_stable": KnobSpec(1, "estábulo mínimo da aldeia ofensiva da conta", integer=True),
    "account.expansion_snob": KnobSpec(1, "academia mínima da aldeia de expansão da conta", integer=True),
}
