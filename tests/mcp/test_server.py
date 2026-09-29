import pytest
from mcp.server.mcpserver.exceptions import ToolError

from tribal_assistant.mcp.server import INSTRUCTIONS, RULES, TribalMcpServer

READ_ONLY_TOOLS = {
    "get_overview",
    "get_village_state",
    "list_barbarians",
    "get_quests",
    "get_agent_decisions",
    "get_agents_config",
    "lookup_knowledge",
    "get_plans",
    "get_world_status",
    "list_nearby",
    "get_coordination",
    "search_docs",
    "read_doc",
    "get_reports",
    "get_forecast",
    "plan_scavenge",
    "get_market",
    "get_knight",
    "get_inventory",
    "get_knobs",
}
READS_GAME_TOOLS = {"get_market", "get_knight", "get_inventory"}
GAME_ACTIONS = {
    "run_agents",
    "upgrade_building",
    "recruit_units",
    "send_farm_attack",
    "claim_quest_rewards",
    "complete_quest",
    "send_scavenge",
    "unlock_scavenge",
    "open_daily_bonus",
}
LOCAL_WRITES = {"set_village_goal", "set_village_plan", "update_agent_settings", "set_village_role"}
PROMPTS = {"grow_village", "farm_round", "first_noble_plan", "agent_round", "daily_routine"}


@pytest.fixture
def server(client):
    from httpx import ASGITransport

    from tribal_assistant.api.app import app
    from tribal_assistant.mcp.client import ApiClient

    api = ApiClient(base_url="http://test", transport=ASGITransport(app=app))
    return TribalMcpServer(api).build()


async def _tools(server) -> dict:
    return {tool.name: tool for tool in await server.list_tools()}


async def test_tool_surface(server) -> None:
    tools = await _tools(server)

    assert set(tools) == READ_ONLY_TOOLS | GAME_ACTIONS | LOCAL_WRITES | {"sync_account", "sync_world"}
    assert len(tools) == 35
    for tool in tools.values():
        assert tool.description
        assert tool.title
        assert tool.input_schema["type"] == "object"
        assert tool.output_schema is not None
        assert tool.annotations is not None


async def test_annotations_match_side_effects(server) -> None:
    tools = await _tools(server)

    for name in READ_ONLY_TOOLS:
        assert tools[name].annotations.read_only_hint, name
        assert tools[name].annotations.open_world_hint == (name in READS_GAME_TOOLS), name
    for name in GAME_ACTIONS:
        assert not tools[name].annotations.read_only_hint, name
        assert tools[name].annotations.open_world_hint, name
    for name in LOCAL_WRITES:
        assert not tools[name].annotations.open_world_hint, name
        assert tools[name].annotations.destructive_hint, name
    assert tools["send_farm_attack"].annotations.destructive_hint
    assert tools["sync_account"].annotations.read_only_hint


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
    assert prompts == PROMPTS

    text = "\n".join(m.content.text for m in (await server.get_prompt("agent_round", {})).messages)
    assert text.index("get_agents_config") < text.index("run_agents") < text.index("get_agent_decisions")


async def test_prompts_require_dry_run_first(server) -> None:
    for name in PROMPTS - {"first_noble_plan"}:
        text = "\n".join(m.content.text for m in (await server.get_prompt(name, {})).messages)
        assert "dry_run=true" in text, name


async def test_prompt_uses_given_village(server) -> None:
    result = await server.get_prompt("grow_village", {"village_id": "42"})

    assert "Village: 42." in result.messages[0].content.text


async def test_plan_tool_bounds_steps(server) -> None:
    tools = await _tools(server)
    steps = tools["set_village_plan"].input_schema["properties"]["steps"]

    assert steps["maxItems"] == 12
    assert steps["minItems"] == 1


async def test_knowledge_resources(server) -> None:
    uris = {str(r.uri) for r in await server.list_resources()}
    templates = {t.uri_template for t in await server.list_resource_templates()}

    assert {"tribal://knowledge/strategy", "tribal://knowledge/buildings", "tribal://knowledge/units", "tribal://plans"} <= uris
    assert "tribal://village/{village_id}/state" in templates

    contents = list(await server.read_resource("tribal://knowledge/buildings"))
    assert '"snob"' in contents[0].content


async def test_insight_tools_read_through_the_api(server) -> None:
    reports = await server.call_tool("get_reports", {"limit": 5})
    forecast = await server.call_tool("get_forecast", {})
    scavenge = await server.call_tool("plan_scavenge", {})

    assert reports.structured_content["total"] == 0
    assert forecast.structured_content == {"villages": []}
    assert scavenge.structured_content == {"villages": []}


async def test_knobs_tool_reads_through_the_api(server) -> None:
    result = await server.call_tool("get_knobs", {})
    knobs = result.structured_content["knobs"]

    assert knobs
    assert {"name", "value", "default", "reason", "self_tuning"} <= set(knobs[0])
