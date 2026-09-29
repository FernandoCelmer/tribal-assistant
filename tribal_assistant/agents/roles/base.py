"""A specialist that runs on every own village each round."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from tribal_assistant.agents.context import VillageContext
from tribal_assistant.agents.knowledge import GameKnowledge
from tribal_assistant.agents.plan import PlanTracker
from tribal_assistant.agents.view import ContextView
from tribal_assistant.schemas.agent_settings import AgentSettings

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox

RULES = """\
Regras:
- Você age só nesta aldeia e só com as ferramentas que recebeu.
- O estado da aldeia já está na mensagem; só chame ferramentas de leitura para conferir o efeito de uma ação.
- As travas valem sempre: reserva de recursos, orçamento de recrutamento, vagas na fila, raio de ataque, \
limite de ataques por hora, intervalo entre ataques ao mesmo alvo e só aldeias bárbaras.
- Resposta RECUSADO é final: não repita a mesma chamada nem tente contornar; ajuste ou pare.
- Nunca gaste pontos premium, nunca ataque jogadores, nunca venda nem envie recursos.
- Com ATAQUES CHEGANDO no estado, tropas ficam em casa.
- Toda ação leva um "reason" curto (até 8 palavras), ex.: "missão: Bosque 5".
- Economize: no máximo 5 chamadas, sem texto entre elas; se nada for útil, não chame ferramentas.
- Resposta final: uma frase em português com o que fez e o próximo passo, ou por que não fez nada.
"""


class VillageAgent(ABC):
    """Role, prompt and fallback policy of one specialist."""

    key: str
    title: str
    mission: str
    tools: tuple[str, ...]
    buildings: tuple[str, ...] = ()

    def system_prompt(self) -> str:
        area = f"\nEdifícios da sua área: {', '.join(self.buildings)}." if self.buildings else ""
        return f"Você é o {self.title} de uma aldeia no Tribal Wars (servidor brasileiro).\nMissão: {self.mission}{area}\n\n{RULES}"

    def task_prompt(self, ctx: VillageContext, config: AgentSettings) -> str:
        return (
            f"{ContextView(ctx, config.build_queue_slots).render(self.key)}\n\n"
            "Decida e aja nesta rodada seguindo sua missão e as regras."
        )

    def needs_llm(self, ctx: VillageContext, config: AgentSettings) -> bool:
        return True

    @abstractmethod
    async def rules(self, box: "Toolbox") -> str:
        """Deterministic behaviour used when AI is off for this agent or fails."""

    @staticmethod
    def quest_targets(ctx: VillageContext) -> list[tuple[str, int]]:
        targets = []

        for quest in ctx.quests:
            for goal in quest.get("goals", []):
                current, target = goal.get("current"), goal.get("target")
                if current is not None and target is not None and current >= target:
                    continue

                mapped = GameKnowledge.goal_building(f"{goal.get('title', '')} {goal.get('text', '')}")
                if mapped and ctx.levels.get(mapped[0], 0) < mapped[1]:
                    targets.append(mapped)

        return targets

    def free_slots(self, box: "Toolbox") -> int:
        return max(0, box.config.build_queue_slots - len(box.ctx.queue))

    async def build_first_affordable(self, box: "Toolbox", candidates: list[str], limit: int, reason: str) -> list[str]:
        done = []
        planned = set(PlanTracker.next_builds(box.ctx.plan))

        for building in dict.fromkeys(candidates):
            if len(done) >= limit or not self.free_slots(box):
                break
            if building not in self.buildings and building not in planned:
                continue
            if box.guard.check_upgrade(box.ctx, building):
                continue

            outcome = await box.invoke("upgrade_building", {"building": building, "reason": reason})
            if outcome.ok:
                done.append(building)

        return done

    @staticmethod
    def near_full(ctx: VillageContext, ratio: float = 0.85) -> bool:
        storage = ctx.village.storage or 1
        return any(value >= storage * ratio for value in ctx.stock.values())
