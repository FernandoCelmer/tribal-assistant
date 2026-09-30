"""A specialist that runs on every own village each round."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.view import ContextView
from tribal_assistant.core.schemas.agent_settings import AgentSettings

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox

RULES = """\
Regras:
- Você age só nesta aldeia e só com as ferramentas que recebeu.
- O estado da aldeia já está na mensagem; só chame ferramentas de leitura para conferir o efeito de uma ação.
- As travas valem sempre: reserva de recursos, orçamento de recrutamento, vagas na fila, raio de ataque, \
limite de ataques por hora, intervalo entre ataques ao mesmo alvo e só aldeias bárbaras.
- Resposta RECUSADO é final: não repita a mesma chamada nem tente contornar; ajuste ou pare.
- Nunca gaste pontos premium e nunca ataque jogadores; nobres só conquistam aldeias bárbaras.
- Recursos só saem por troca no mercado ou por send_resources para aldeias suas desta mesma conta; \
nunca envie recursos para outros jogadores nem para outras contas.
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
            f"{ContextView(ctx, ctx.policy.build_queue_slots).render(self.key)}\n\n"
            "Decida e aja nesta rodada seguindo sua missão e as regras."
        )

    def needs_llm(self, ctx: VillageContext, config: AgentSettings) -> bool:
        return True

    @abstractmethod
    async def rules(self, box: "Toolbox") -> str:
        """Deterministic behaviour used when AI is off for this agent or fails."""
