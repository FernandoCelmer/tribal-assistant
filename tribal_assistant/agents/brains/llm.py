"""Language-model brain: a tool-calling loop over the agent's toolbox."""

from typing import TYPE_CHECKING, Any

from loguru import logger

from tribal_assistant.agents.brains.base import Brain
from tribal_assistant.agents.brains.rules import RuleBrain
from tribal_assistant.ai.abc.llm import LLM
from tribal_assistant.ai.errors import LLMError
from tribal_assistant.core.config import settings

if TYPE_CHECKING:
    from tribal_assistant.agents.roles.base import VillageAgent
    from tribal_assistant.agents.toolbox import Toolbox


class LLMBrain(Brain):
    name = "llm"

    def __init__(self, llm: LLM, max_steps: int | None = None) -> None:
        self.llm = llm
        self.max_steps = max_steps or settings.ai_max_steps
        self.fallback = RuleBrain()

    async def act(self, agent: "VillageAgent", box: "Toolbox") -> str:
        system = agent.system_prompt()
        task = agent.task_prompt(box.ctx, box.config)
        conversation = self.llm.conversation(system, task, box.specs())

        await self._trace(box, "prompt", f"[{self.llm.provider} {self.llm.model}]\n\n{system}\n\n---\n\n{task}")

        try:
            reply = await self._send(box, conversation)

            for _ in range(self.max_steps):
                if not reply.tool_calls:
                    break

                results = [await box.call(call) for call in reply.tool_calls]
                reply = await self._send(box, conversation, results)

        except LLMError as exc:
            logger.warning("{} on {}: {}; falling back to rules", agent.key, self.llm.provider, exc)
            await self._trace(box, "error", f"IA indisponível: {exc}", is_error=True)
            return f"IA indisponível ({exc}); regras: {await self.fallback.act(agent, box)}"

        if reply.stop == "refusal":
            return f"modelo recusou; regras: {await self.fallback.act(agent, box)}"

        return reply.text.strip() or "sem resumo"

    async def _send(self, box: "Toolbox", conversation: Any, results: Any = None) -> Any:
        reply = await conversation.send(results)

        if box.trace is not None:
            box.trace.usage(reply.tokens_in, reply.tokens_out)

        if reply.text.strip():
            await self._trace(box, "thought", reply.text.strip())

        return reply

    @staticmethod
    async def _trace(box: "Toolbox", kind: str, content: str, *, is_error: bool = False) -> None:
        if box.trace is not None:
            await box.trace.step(kind, content, is_error=is_error)
