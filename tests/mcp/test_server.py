import pytest
from mcp.server.mcpserver.exceptions import ToolError

from tribal_assistant.mcp.server import INSTRUCTIONS, RULES, TribalMcpServer

READ_ONLY_TOOLS = {
    "get_overview",
    "get_quests",
    "get_agent_decisions",
    "get_agents_config",
    "lookup_knowledge",
    "get_plans",
    "get_world_status",
    "list_nearby",
    "list_farm_targets",
}
GAME_ACTIONS = {
    "run_agents",
    "upgrade_building",
    "recruit_units",
    "send_farm_attack",
    "claim_quest_rewards",
    "complete_quest",
}


@pytest.fixture
def server():
    return TribalMcpServer().build()


async def _tools(server) -> dict:
    return {tool.name: tool for tool in await server.list_tools()}


async def test_tool_surface(server) -> None:
    tools = await _tools(server)

    assert set(tools) == READ_ONLY_TOOLS | GAME_ACTIONS | {
        "sync_account",
        "sync_world",
        "add_farm_target",
        "remove_farm_target",
        "set_village_goal",
        "update_agent_settings",
    }
    for tool in tools.values():
        assert tool.description
        assert tool.input_schema["type"] == "object"
        assert tool.output_schema is not None
        assert tool.annotations is not None


async def test_annotations_match_side_effects(server) -> None:
    tools = await _tools(server)

    for name in READ_ONLY_TOOLS:
        assert tools[name].annotations.read_only_hint, name
    for name in GAME_ACTIONS:
        assert not tools[name].annotations.read_only_hint, name
        assert tools[name].annotations.open_world_hint, name


async def test_game_actions_default_to_dry_run(server) -> None:
    tools = await _tools(server)

    for name in GAME_ACTIONS:
        assert tools[name].input_schema["properties"]["dry_run"]["default"] is True, name


async def test_rules_are_in_instructions(server) -> None:
    assert server.instructions == INSTRUCTIONS + RULES
    assert "dry_run=true" in server.instructions
    assert "RECUSADO" in server.instructions


async def test_lookup_knowledge_call(server) -> None:
    result = await server.call_tool("lookup_knowledge", {"kind": "building", "id": "snob"})

    assert result.structured_content["requires"] == {"market": 10, "main": 20, "smith": 20}


async def test_unknown_knowledge_is_a_tool_error(server) -> None:
    with pytest.raises(ToolError, match="desconhecido"):
        await server.call_tool("lookup_knowledge", {"kind": "unit", "id": "dragon"})


async def test_prompts_name_tools_in_order(server) -> None:
    prompts = {p.name for p in await server.list_prompts()}
    assert prompts == {"grow_village", "farm_round", "first_noble_plan", "agent_round"}

    text = "\n".join(m.content.text for m in (await server.get_prompt("agent_round", {})).messages)
    assert text.index("get_agents_config") < text.index("run_agents") < text.index("get_agent_decisions")
