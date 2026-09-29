"""Runs one agent tool for one village as the operator, through the guardrails and the decision log."""

from typing import Any
from uuid import uuid4

from tribal_assistant.agents.context import ContextLoader
from tribal_assistant.agents.roles.operator import OperatorAgent
from tribal_assistant.agents.toolbox import Toolbox
from tribal_assistant.agents.tools.base import ToolOutcome
from tribal_assistant.core.errors import NotFoundError
from tribal_assistant.mcp.tools.base import ToolGroup
from tribal_assistant.repositories.agent_settings import AgentSettingsRepository


class ToolboxBridge:
    SOURCE = "mcp"

    def __init__(self) -> None:
        self.operator = OperatorAgent()

    async def invoke(self, village_id: int, tool: str, arguments: dict[str, Any], dry_run: bool) -> ToolOutcome:
        async def run(session: Any) -> ToolOutcome:
            contexts = await ContextLoader(session).load([village_id])
            if not contexts:
                raise NotFoundError(f"aldeia {village_id} não sincronizada: rode sync_account e veja get_overview")

            box = Toolbox(
                agent=self.operator,
                ctx=contexts[0],
                session=session,
                config=await AgentSettingsRepository(session).get(),
                run_id=f"{self.SOURCE}-{uuid4().hex[:8]}",
                dry_run=dry_run,
            )
            box.brain_name = self.SOURCE

            return await box.invoke(tool, arguments)

        return await ToolGroup.with_session(run)
