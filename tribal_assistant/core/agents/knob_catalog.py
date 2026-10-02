"""Every tunable number the agents decide with: default, meaning and the rule that moves it."""

from dataclasses import fields

from tribal_assistant.core.agents.coordination.strategy import (
    PENALTIES,
    SPECIALISTS,
    WEIGHTS,
    Weights,
)
from tribal_assistant.core.agents.knob_rules import (
    KnobSpec,
    cooldown,
    cooldowns,
    either,
    exploration,
    factor_yield,
    less_when,
    less_when_many,
    more_when,
    settle,
    settle_when_few,
    specialist_yield,
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
ARMY_STALLED_UP = more_when("army_stalled", 0.9, "rodadas sem recrutar nada")
IRON_CALM = settle("iron_short", 0.1, "obras esperando ferro")
IRON_SHORT_UP = more_when("iron_short", 0.3, "obras esperando ferro")
IRON_SHORT_DOWN = less_when("iron_short", 0.3, "obras esperando ferro")
STORAGE_UP_OR_CALM = either(STORAGE_FULL_UP, STORAGE_CALM)
STORAGE_DOWN_OR_CALM = either(STORAGE_FULL_DOWN, STORAGE_CALM)
NOBLES_FAILED_UP = either(more_when("nobles_failed", 0.3, "nobres falhando"), settle("nobles_failed", 0.05, "nobres falhando"))
MAIL_CAPPED_UP = either(more_when("mail_capped", 0.5, "respostas barradas pelo limite por hora"), settle("mail_capped", 0.05, "respostas barradas pelo limite por hora"))
CONTACTS_IGNORED_DOWN = either(less_when("contacts_unanswered", 0.8, "apresentações sem resposta"), settle("contacts_unanswered", 0.5, "apresentações sem resposta"))
BUILDS_DONE = either(less_when_many("builds_done", 3, "níveis de edifício concluídos na janela"), settle_when_few("builds_done", 1, "níveis de edifício concluídos na janela"))
SOCIAL_IDLE_DOWN = either(less_when("social_idle", 0.8, "tempo sem nenhuma ação social"), settle("social_idle", 0.3, "tempo sem nenhuma ação social"))
SOCIAL_IDLE_UP = either(more_when("social_idle", 0.8, "tempo sem nenhuma ação social"), settle("social_idle", 0.3, "tempo sem nenhuma ação social"))
LEARNING_MARGIN = 0.15
SHIPMENTS_FAILED_UP = either(more_when("shipments_failed", 0.3, "envios entre aldeias falhando"), settle("shipments_failed", 0.05, "envios entre aldeias falhando"))


def _policy() -> dict[str, KnobSpec]:
    rules = {
        "resource_reserve": (either(STOCK_EMPTY, STARVED, less_when("army_stalled", 0.75, "rodadas sem recrutar nada")), True, False, "fração do armazém reservada"),
        "recruit_budget": (
            either(less_when("idle_recruiting", 0.3, "fila de obras parada enquanto recrutava"), STORAGE_FULL_UP, more_when("army_stalled", 0.9, "rodadas sem recrutar nada")),
            True,
            False,
            "fração da sobra que o recrutamento pode gastar",
        ),
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
            rule = factor_yield(role.value, item.name, item.name in PENALTIES, LEARNING_MARGIN)
            specs[f"weight.{role.value}.{item.name}"] = KnobSpec(getattr(weights, item.name), f"peso de {item.name} na prioridade do papel {role.value}", rule, share=True)
    return specs


def _bonuses() -> dict[str, KnobSpec]:
    return {
        f"bonus.{source}": KnobSpec(1.0, f"multiplicador aprendido da prioridade das propostas de {source}, pelo que elas renderam", specialist_yield(source, LEARNING_MARGIN))
        for source in SPECIALISTS
    }


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
    "raid.min_carry_share": KnobSpec(0.5, "fração mínima do saque desejado que o grupo precisa carregar", less_when("no_targets", 0.3, "sem alvos viáveis"), share=True),
    "raid.yellow_streak_skip": KnobSpec(2, "relatórios amarelos seguidos antes de pular o alvo até espionar", integer=True),
    "raid.escort_spies": KnobSpec(1, "exploradores que acompanham um saque em alvo sem muralha", integer=True),
    "raid.unknown_fill_share": KnobSpec(0.5, "fração da carga que se espera de um alvo sem histórico", share=True),
    "plan.spear_min": KnobSpec(40, "lanceiros que o plano automático pede antes da cavalaria leve", integer=True),
    "plan.spear_step": KnobSpec(10, "lanceiros por passo do plano automático", integer=True),
    "plan.max_steps": KnobSpec(12, "passos guardados no plano da aldeia", integer=True),
    "plan.recruit_lookahead": KnobSpec(2, "passos de recrutamento do plano olhados por rodada", integer=True),
    "recruit.max_queued_batches": KnobSpec(2, "lotes de lanceiros na fila antes de esperar", ARMY_STALLED_UP, integer=True),
    "build.plan_lookahead": KnobSpec(4, "obras do plano propostas por rodada", IDLE_QUEUE_UP, integer=True),
    "build.unlock_lookahead": KnobSpec(1, "desbloqueios de coleta propostos por rodada", integer=True),
    "browse.neighbours": KnobSpec(3, "perfis de vizinhos no sorteio do passeio", integer=True),
    "browse.tribes": KnobSpec(2, "tribos próximas no sorteio do passeio", integer=True),
    "social.first_contact_window_hours": KnobSpec(24, "janela em horas do limite de primeiros contatos"),
    "social.send_window_hours": KnobSpec(1, "janela em horas do limite de mensagens"),
    "defense.hold_margin_hours": KnobSpec(0.25, "horas que as tropas ficam seguradas depois do impacto"),
    "defense.urgency_horizon_hours": KnobSpec(6, "horas até o impacto em que a defesa passa a ter urgência"),
    "plan.iron_lookahead": KnobSpec(2, "próximas obras do plano cujo ferro é guardado", integer=True),
    "plan_reserve.lookahead": KnobSpec(1, "próximas obras do plano com recursos reservados", integer=True),
    "defense.hide_level_danger": KnobSpec(7, "esconderijo mínimo com vizinhos perigosos", integer=True),
    "defense.hide_level_near": KnobSpec(5, "esconderijo mínimo com vizinhos por perto", integer=True),
    "defense.hide_level_calm": KnobSpec(3, "esconderijo mínimo sem vizinhos", integer=True),
    "recruit.overflow_units": KnobSpec(1, "tipos de tropa de saque recrutados com o armazém quase cheio", STORAGE_FULL_UP, integer=True),
    "farm.pressure_ratio": KnobSpec(0.15, "fração de população livre abaixo da qual a fazenda aperta", share=True),
    "build.recruit_demand_units": KnobSpec(10, "unidades do próximo recrutamento somadas à demanda de recursos", integer=True),
    "knight.train_max_share": KnobSpec(0.5, "fração do menor recurso que um treino do paladino pode custar com o armazém cheio", share=True),
    "plan.storage_for_stable": KnobSpec(6, "nível do armazém no caminho do estábulo", integer=True),
    "plan.storage_cost_share": KnobSpec(0.95, "fração do armazém que uma obra pode custar antes de pedir armazém maior", share=True),
    "learning.min_samples": KnobSpec(4, "resultados mínimos antes de aprender o bônus de um especialista", integer=True),
    "learning.high_factor": KnobSpec(0.5, "valor de um fator a partir do qual a proposta conta como forte nele", share=True),
    "goal.max_age_hours": KnobSpec(24, "horas até um objetivo da aldeia sem revisão deixar de valer"),
    "reflection.interval_hours": KnobSpec(2, "horas entre reflexões sobre como o jogo foi"),
    "reflection.window_hours": KnobSpec(3, "horas de jogo que cada reflexão mede"),
    "reflection.half_life_hours": KnobSpec(24, "horas para a confiança de uma conclusão não conferida cair pela metade"),
    "reflection.step": KnobSpec(0.15, "quanto uma conclusão ganha de confiança quando a medida confirma", share=True),
    "reflection.margin": KnobSpec(0.05, "mudança mínima da medida para confirmar ou contrariar uma conclusão", share=True),
    "reflection.drop_below": KnobSpec(0.2, "confiança abaixo da qual a conclusão é descartada", share=True),
    "reflection.initial_confidence": KnobSpec(0.5, "confiança de uma conclusão nova", share=True),
    "reflection.max_beliefs": KnobSpec(8, "conclusões ativas ao mesmo tempo", integer=True),
    "sightings.inactive_hours": KnobSpec(24, "horas com os mesmos pontos até um vizinho visitado contar como inativo"),
    "threat.expanding_hours": KnobSpec(48, "horas em que um vizinho visto ganhando aldeias conta como ameaça"),
    "tuner.interval_minutes": KnobSpec(10, "minutos entre passadas do ajuste automático dos knobs"),
    "tuner.window_hours": KnobSpec(3, "horas de rodadas que o ajuste automático mede"),
    "tuner.max_streak": KnobSpec(6, "passos seguidos no mesmo sentido sem resolver o problema antes de o knob voltar ao padrão", integer=True),
    "tuner.blocked_hours": KnobSpec(24, "horas em que um sentido que não resolveu fica fechado para o knob"),
    "tuner.min_rounds": KnobSpec(4, "rodadas jogadas com o valor atual de um knob antes de ele poder mudar de novo", integer=True),
    "absence.min_minutes": KnobSpec(60, "minutos sem rodada que contam como ausência do bot"),
    "absence.recall_hours": KnobSpec(2, "horas em que os agentes ainda veem o resumo da última ausência"),
    "absence.habit_hours": KnobSpec(3, "horas mínimas de uma ausência para entrar no padrão de paradas"),
    "absence.prepare_minutes": KnobSpec(60, "minutos antes da parada provável em que a aldeia se prepara para ela"),
    "runner.stale_minutes": KnobSpec(15, "minutos até uma rodada presa ser dada como interrompida", integer=True),
    "research.reserve_hours": KnobSpec(6, "horas até a próxima pesquisa ficar pronta para começar a guardar recursos para ela"),
    "routine.recruit_share": KnobSpec(0.15, "fração do estoque que a rotina pode gastar num lote de recrutamento", either(ARMY_STALLED_UP, STORAGE_FULL_UP), share=True),
    "routine.recruit_queue_minutes": KnobSpec(30, "minutos de fila no quartel abaixo dos quais a rotina recruta mais", ARMY_STALLED_UP),
    "routine.scavenge_keep_share": KnobSpec(0.01, "fração das tropas em casa que a rotina deixa fora da coleta", share=True),
    "learning.bonus_cap": KnobSpec(1.4, "maior bônus aprendido que um especialista pode ter no ranking", more_when("repetition", 0.5, "rodadas repetindo as mesmas ações")),
    "build.unaffordable_kept": KnobSpec(1, "obras que ainda não cabem no estoque mantidas no ranking de uma rodada", integer=True),
    "raid.probe_fresh_hours": KnobSpec(6, "horas em que uma sonda recente dispensa sondar o mesmo alvo de novo"),
    "plan.refresh_minutes": KnobSpec(120, "minutos até o estrategista refazer o plano da aldeia com a IA quando nada mudou"),
    "quests.refresh_minutes": KnobSpec(15, "minutos entre leituras da janela de missões quando o jogo não avisa novidade"),
    "routine.troops_retry_minutes": KnobSpec(5, "minutos de espera da rotina de tropas depois de uma passada sem nada para enviar"),
    "watch.rounds": KnobSpec(8, "rodadas recentes que o vigia olha em cada aldeia", integer=True),
    "watch.stuck_rounds": KnobSpec(5, "rodadas travadas (estoque todo reservado e fila parada) antes de o vigia agir", integer=True),
    "watch.suppress_hours": KnobSpec(2, "horas em que uma reserva suspensa pelo vigia fica sem valer"),
    "spy.min_send": KnobSpec(5, "exploradores mínimos por envio de espionagem (o jogo recusa menos)", integer=True),
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
    "cooldown.profile": KnobSpec(2, "horas entre tentativas de escrever o texto do perfil para a missão", cooldown("set_profile_text")),
    "cooldown.tribe": KnobSpec(6, "horas entre buscas de tribo", cooldowns("apply_to_tribe", "accept_tribe_invite")),
    "cooldown.mentor": KnobSpec(8, "horas entre buscas de mentor", cooldown("accept_mentor")),
    "cooldown.smith": KnobSpec(1, "horas entre visitas ao ferreiro", cooldown("research_unit")),
    "cooldown.daily_bonus": KnobSpec(4, "horas entre aberturas do bônus diário", cooldown("open_daily_bonus")),
    "diplomacy.apply_retry_hours": KnobSpec(48, "horas antes de pedir de novo à mesma tribo"),
    "diplomacy.apply_wait_hours": KnobSpec(48, "horas sem resposta de uma candidatura antes de tentar a próxima tribo", cooldown("apply_to_tribe")),
    "diplomacy.parallel_applications": KnobSpec(2, "candidaturas abertas ao mesmo tempo", integer=True),
    "diplomacy.min_members": KnobSpec(5, "membros mínimos de uma tribo candidata", integer=True),
    "diplomacy.search_radius": KnobSpec(20, "raio em campos da busca de tribos nos dados do mundo", integer=True),
    "diplomacy.forums_read": KnobSpec(2, "subfóruns da tribo lidos por visita", integer=True),
    "cooldown.mail": KnobSpec(0.5, "horas entre leituras da caixa de entrada", cooldown("reply_mail")),
    "cooldown.buddies": KnobSpec(2, "horas entre visitas à lista de amigos", either(cooldowns("accept_friend", "add_friend"), SOCIAL_IDLE_DOWN)),
    "cooldown.friend_request": KnobSpec(4, "horas entre pedidos de amizade enviados", either(cooldown("add_friend"), SOCIAL_IDLE_DOWN)),
    "cooldown.outreach": KnobSpec(2, "horas entre apresentações a jogadores novos", either(cooldown("send_mail"), SOCIAL_IDLE_DOWN)),
    "cooldown.browse": KnobSpec(0.5, "horas entre passeios pelas páginas do jogo", either(cooldown("browse_game"), SOCIAL_IDLE_DOWN)),
    "browse.pages": KnobSpec(4, "páginas visitadas em cada passeio pelo jogo", integer=True),
    "cooldown.tribe_read": KnobSpec(3, "horas entre leituras do fórum, anúncios e membros da tribo", cooldown("reply_forum")),
    "social.messages_per_hour": KnobSpec(5, "mensagens enviadas por hora (respostas, apresentações e fórum)", MAIL_CAPPED_UP, integer=True),
    "social.first_contacts_per_day": KnobSpec(5, "primeiros contatos com jogadores novos por dia", either(less_when("contacts_unanswered", 0.8, "apresentações sem resposta"), more_when("social_idle", 0.8, "tempo sem nenhuma ação social"), CONTACTS_IGNORED_DOWN), integer=True),
    "social.replies_per_round": KnobSpec(3, "conversas respondidas por rodada", MAIL_CAPPED_UP, integer=True),
    "social.threads_per_round": KnobSpec(5, "conversas abertas e lidas por rodada", integer=True),
    "social.history_messages": KnobSpec(12, "mensagens da conversa que a IA lê antes de responder", integer=True),
    "social.friend_target": KnobSpec(10, "amizades buscadas (a conquista Amigo fiel pede 5)", integer=True),
    "social.neighbour_radius": KnobSpec(10, "raio em campos de um vizinho para amizade e apresentação", SOCIAL_IDLE_UP, integer=True),
    "social.active_growth": KnobSpec(5, "pontos por hora entre duas fotos para um jogador ou tribo contar como ativo", SOCIAL_IDLE_DOWN),
    "social.snapshot_hours": KnobSpec(1, "horas mínimas entre duas fotos de pontos para medir o ritmo de quem está ativo", SOCIAL_IDLE_DOWN),
    "social.activity_window_hours": KnobSpec(24, "idade máxima em horas da foto de pontos mais antiga usada para medir o ritmo"),
    "social.active_share": KnobSpec(0.5, "fração dos nossos pontos que torna provável um vizinho ainda sem histórico estar ativo", SOCIAL_IDLE_DOWN, share=True),
    "social.follow_up_hours": KnobSpec(1, "horas depois da candidatura para escrever ao líder da tribo", SOCIAL_IDLE_DOWN),
    "pacing.main_early_cap": KnobSpec(10, "edifício principal antes do portão do estábulo", IDLE_QUEUE_UP, integer=True),
    "pacing.main_late_cap": KnobSpec(20, "edifício principal depois do portão do estábulo", IDLE_QUEUE_UP, integer=True),
    "pacing.stable_gate": KnobSpec(3, "nível do estábulo que libera o edifício principal", integer=True),
    "pacing.military_every": KnobSpec(3, "níveis do edifício principal por degrau militar", integer=True),
    "pacing.military_step": KnobSpec(2, "níveis de quartel e estábulo pedidos por degrau", integer=True),
    "pacing.barracks_base": KnobSpec(5, "quartel pedido no primeiro degrau militar", integer=True),
    "economy.light_research_iron": KnobSpec(2000, "ferro guardado para pesquisar a cavalaria leve", integer=True),
    "market.max_lot": KnobSpec(1000, "maior oferta de mercado de uma vez", STORAGE_FULL_UP, integer=True),
    "scavenge.min_pop": KnobSpec(10, "população mínima que o jogo aceita numa coleta (aprendida do erro)", integer=True),
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
    "farm.template_a_carry": KnobSpec(400, "carga do modelo A do assistente de saque (grupo pequeno, muralha 0)", either(more_when("farm_full", 0.6, "saques do assistente voltando cheios"), less_when("farm_partial", 0.8, "saques do assistente voltando com sobra")), integer=True),
    "farm.template_b_carry": KnobSpec(1200, "carga do modelo B do assistente de saque (grupo maior, cheio recorrente ou muralha 1-2)", either(more_when("farm_full", 0.4, "saques do assistente voltando cheios"), less_when("farm_partial", 0.8, "saques do assistente voltando com sobra")), integer=True),
    "farm.full_streak_b": KnobSpec(2, "saques cheios seguidos que mandam o alvo para o modelo B", either(less_when("farm_full", 0.6, "saques do assistente voltando cheios"), settle("farm_full", 0.2, "saques do assistente voltando cheios")), integer=True),
    "farm.template_tolerance": KnobSpec(0.25, "diferença entre o modelo salvo e o ideal que pede salvar de novo", share=True),
    "farm.recheck_hours": KnobSpec(6, "horas até olhar de novo um assistente de saque indisponível"),
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
    "learning.requirement_hours": KnobSpec(12, "horas sem repetir uma ação que o jogo recusou por requisito não atendido"),
    "learning.repeat_limit": KnobSpec(2, "falhas iguais antes de bloquear a ação", integer=True),
    "session.lease_minutes": KnobSpec(3, "minutos sem uso até outra máquina poder assumir o jogo da conta"),
    "coordinator.min_review_minutes": KnobSpec(2, "minutos mínimos até a próxima revisão da aldeia"),
    "coordinator.max_actions": KnobSpec(10, "ações por rodada", either(more_when("actions_capped", 0.3, "rodadas no limite de ações"), settle("actions_capped", 0.05, "rodadas no limite de ações")), integer=True),
    "coordinator.recent_minutes": KnobSpec(10, "minutos em que uma ação feita espera o jogo confirmar", integer=True),
    "coordinator.explore_rate": KnobSpec(0.1, "chance de a rodada explorar uma proposta viável que não seria a primeira", exploration(0.5, -LEARNING_MARGIN, 4), share=True),
    "coordinator.repeat_rounds": KnobSpec(3, "rodadas seguidas com as mesmas ações que contam como repetição", integer=True),
    **_weights(),
    **_bonuses(),
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
    "timelapse.interval_hours": KnobSpec(3.0, "horas entre fotos da aldeia no timelapse (cai quando muitas obras terminam)", BUILDS_DONE),
    "timelapse.min_interval_hours": KnobSpec(0.5, "menor intervalo em horas entre fotos do timelapse"),
    "timelapse.quality": KnobSpec(70, "qualidade JPEG das fotos do timelapse", integer=True),
    "timelapse.max_kb": KnobSpec(150, "tamanho máximo em KB de uma foto do timelapse antes de baixar a qualidade", integer=True),
    "account.expansion_snob": KnobSpec(1, "academia mínima da aldeia de expansão da conta", integer=True),
}
