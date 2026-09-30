"""When an action fails, read the game's error and try once more with corrected arguments."""

import json
import re
from typing import Any

from tribal_assistant.core.agents.tools.base import AgentTool
from tribal_assistant.core.agents.writer import ModelWriter

SYSTEM = (
    "Você corrige chamadas de ferramentas de um bot de Tribal Wars (servidor brasileiro). Recebe a ferramenta, o esquema "
    "dos argumentos, os argumentos usados, a mensagem de erro do jogo e o estado resumido da aldeia. Se o erro se resolve "
    "mudando os argumentos (quantidade mínima, unidade, alvo de bárbara, formato), responda só um objeto JSON com os "
    "argumentos corrigidos e completos. Se não há correção pelos argumentos (faltam recursos, requisito não atendido, "
    "espera, limite por hora, tela indisponível), responda null. Nunca troque o alvo por um jogador, nunca use pontos premium."
)
UNFIXABLE = re.compile(r"^RECUSADO|faltam |recursos insuficientes|aguard|limite|requisito|deve ter pelo menos|já |indisponível|não está livre|não está disponível|em andamento|só há|em casa|não encontrad|não mudou", re.I)
FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class ErrorRepair(ModelWriter):
    @staticmethod
    def worth(error: str) -> bool:
        return bool(error) and not UNFIXABLE.search(error)

    @staticmethod
    def parse(reply: str | None) -> dict[str, Any] | None:
        if not reply:
            return None
        try:
            found = json.loads(FENCE.sub("", reply.strip()))
        except ValueError:
            return None
        return found if isinstance(found, dict) else None

    @staticmethod
    def valid(tool: AgentTool, arguments: dict[str, Any]) -> bool:
        schema = tool.parameters
        known = set(schema.get("properties") or {})
        return set(arguments) <= known and all(name in arguments for name in schema.get("required") or [])

    async def fix(self, tool: AgentTool, arguments: dict[str, Any], error: str, facts: dict[str, Any]) -> dict[str, Any] | None:
        if not self.worth(error):
            return None

        prompt = json.dumps(
            {"ferramenta": tool.name, "descrição": tool.description, "esquema": tool.parameters, "argumentos": arguments, "erro": error, "aldeia": facts},
            ensure_ascii=False,
            default=str,
        )
        corrected = self.parse(await self.ask(SYSTEM, prompt, f"a correção de {tool.name}"))
        if corrected is None:
            return None

        if "reason" in arguments:
            corrected = {**corrected, "reason": arguments["reason"]}
        if not self.valid(tool, corrected) or corrected == arguments:
            return None
        return corrected
