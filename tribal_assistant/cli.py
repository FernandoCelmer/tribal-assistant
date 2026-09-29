"""Command-line interface: `tribal-assistant <command>`."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Literal

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.config import settings
from tribal_assistant.version import __version__

console = Console()
app = typer.Typer(
    name="tribal-assistant",
    help="Tribal Wars account assistant: sync, farm, world data and web dashboard.",
    no_args_is_help=True,
    add_completion=False,
)
farm_app = typer.Typer(help="Farm targets and farm ticks.", no_args_is_help=True)
world_app = typer.Typer(help="Public world data: sync, status, nearby villages.", no_args_is_help=True)
app.add_typer(farm_app, name="farm")
agents_app = typer.Typer(help="Village agents: run a round, read decisions and configuration.", no_args_is_help=True)
app.add_typer(world_app, name="world")
app.add_typer(agents_app, name="agents")

JsonOption = Annotated[bool, typer.Option("--json", help="Print raw JSON instead of a table.")]


def _run[T](coro: Awaitable[T]) -> T:
    return asyncio.run(coro)  # type: ignore[arg-type]


async def _with_session[T](fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    from tribal_assistant.db.session import SessionFactory, init_db

    await init_db()
    async with SessionFactory() as session:
        return await fn(session)


async def _with_game[T](fn: Callable[[], Awaitable[T]]) -> T:
    """Run a browser-backed action and always release the Playwright session."""
    from tribal_assistant.client.session import game_session
    from tribal_assistant.db.session import init_db

    await init_db()
    try:
        return await fn()
    finally:
        await game_session.close()


def _print_json(data: Any) -> None:
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    elif isinstance(data, list):
        data = [d.model_dump(mode="json") if isinstance(d, BaseModel) else d for d in data]
    console.print_json(json.dumps(data, default=str))


def _version(value: bool) -> None:
    if value:
        console.print(f"tribal-assistant {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show version and exit.")
    ] = False,
) -> None:
    from tribal_assistant.core.logging import configure_logging

    configure_logging(settings.log_level)


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Bind address.")] = settings.app_host,
    port: Annotated[int, typer.Option(help="Bind port.")] = settings.app_port,
    reload: Annotated[bool, typer.Option(help="Reload on code changes.")] = settings.app_env == "development",
) -> None:
    """Run the API, the web dashboard and the scheduler."""
    import uvicorn

    uvicorn.run(
        "tribal_assistant.server:app", host=host, port=port, reload=reload, timeout_graceful_shutdown=5
    )


@app.command()
def mcp(
    http: Annotated[bool, typer.Option(help="Serve streamable HTTP instead of stdio.")] = False,
    host: Annotated[str, typer.Option(help="HTTP bind address.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="HTTP port.")] = 8765,
) -> None:
    """Run the MCP server (stdio by default) for Claude, Codex or any MCP client."""
    try:
        from tribal_assistant.mcp.server import main as mcp_main
    except ImportError as exc:
        console.print("[red]MCP não instalado: pip install 'tribal-assistant[mcp]'[/red]")
        raise typer.Exit(1) from exc

    argv = ["--http", "--host", host, "--port", str(port)] if http else []
    mcp_main(argv)


@app.command()
def sync() -> None:
    """Log in and sync player, villages, troops, commands and reports now."""
    from tribal_assistant.services.assistant import AssistantService

    result = _run(_with_game(AssistantService().sync))
    console.print(result.message, style="green" if result.ok else "red")
    if not result.ok:
        raise typer.Exit(1)


@app.command()
def status(as_json: JsonOption = False) -> None:
    """Show the last synced account state (player and villages)."""
    from tribal_assistant.services.game import GameService

    overview = _run(_with_session(lambda s: GameService(s).overview()))
    if as_json:
        _print_json(overview)
        return
    if overview.player is None:
        console.print("Nothing synced yet. Run [bold]tribal-assistant sync[/bold].")
        return

    p = overview.player
    console.print(
        f"[bold]{p.name}[/bold] · {p.world} · {p.points:,} points · rank #{p.rank:,} · "
        f"{p.villages} village(s) · incoming attacks: "
        + (f"[red]{p.incomings}[/red]" if p.incomings else "0")
    )
    table = Table("Village", "Coords", "Points", "Wood", "Clay", "Iron", "Storage", "Pop", "Synced")
    for v in overview.villages:
        table.add_row(
            v.name, v.coords, f"{v.points:,}", f"{v.wood:,}", f"{v.clay:,}", f"{v.iron:,}",
            f"{v.storage:,}", f"{v.pop_current:,}/{v.pop_max:,}",
            v.synced_at.strftime("%Y-%m-%d %H:%M") if v.synced_at else "—",
        )
    console.print(table)
    incoming = [c for c in overview.commands if c.direction == "in" and c.kind in ("attack", "noble")]
    for c in incoming:
        console.print(f"[red]incoming {c.kind}[/red] → {c.village_coords} at {c.arrival_at:%H:%M:%S} · {c.label}")


@farm_app.command("list")
def farm_list(
    all_targets: Annotated[bool, typer.Option("--all", help="Include disabled targets.")] = False,
    as_json: JsonOption = False,
) -> None:
    """List farm targets."""
    from tribal_assistant.repositories.farm import FarmTargetRepository
    from tribal_assistant.schemas.farm import FarmTarget

    rows = _run(_with_session(lambda s: FarmTargetRepository(s).list(enabled_only=not all_targets)))
    targets = [FarmTarget.model_validate(r) for r in rows]
    if as_json:
        _print_json(targets)
        return
    table = Table("ID", "Coords", "Template", "Wall", "Enabled", "Last attack", "Last loot")
    for t in targets:
        table.add_row(
            str(t.id), t.coords, t.template, str(t.wall_level), "yes" if t.enabled else "no",
            t.last_attack_at.strftime("%Y-%m-%d %H:%M") if t.last_attack_at else "—", f"{t.last_loot:,}",
        )
    console.print(table)


@farm_app.command("add")
def farm_add(
    coords: Annotated[str, typer.Argument(help="Target coordinates, e.g. 500|500.")],
    template: Annotated[str, typer.Option(help="Farm assistant template: A, B or C.")] = "A",
    wall: Annotated[int, typer.Option(min=0, max=20, help="Known wall level.")] = 0,
) -> None:
    """Add a farm target."""
    from pydantic import ValidationError

    from tribal_assistant.core.errors import DomainError
    from tribal_assistant.schemas.farm import FarmTargetCreate
    from tribal_assistant.services.farm import FarmService

    try:
        payload = FarmTargetCreate(coords=coords, template=template.upper(), wall_level=wall)
        target = _run(_with_session(lambda s: FarmService(s).add(payload)))
    except (ValidationError, DomainError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(f"added farm target #{target.id} {target.coords} (template {target.template})")


@farm_app.command("remove")
def farm_remove(target_id: Annotated[int, typer.Argument(help="Target ID from `farm list`.")]) -> None:
    """Remove a farm target."""
    from tribal_assistant.core.errors import DomainError
    from tribal_assistant.services.farm import FarmService

    try:
        _run(_with_session(lambda s: FarmService(s).remove(target_id)))
    except DomainError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(f"removed farm target #{target_id}")


@farm_app.command("tick")
def farm_tick() -> None:
    """Send farm attacks against enabled targets now."""
    from tribal_assistant.services.farm import FarmService

    result = _run(_with_game(lambda: _with_session(lambda s: FarmService(s).tick())))
    console.print(f"dispatched: {result.dispatched} · skipped: {result.skipped}")
    for error in result.errors:
        console.print(f"[red]{error}[/red]")
    if result.errors:
        raise typer.Exit(1)


@world_app.command("sync")
def world_sync() -> None:
    """Download the public world data (villages, players, tribes, config)."""
    from tribal_assistant.client.modules.world_sync import sync_world
    from tribal_assistant.db.session import init_db

    async def _sync() -> None:
        await init_db()
        await sync_world()

    _run(_sync())
    console.print("world data synced", style="green")


@world_app.command("status")
def world_status(as_json: JsonOption = False) -> None:
    """Show what world data is stored locally."""
    from tribal_assistant.services.world import WorldService

    data = _run(_with_session(lambda s: WorldService(s).status()))
    if as_json:
        _print_json(data)
        return
    for key, value in data.model_dump().items():
        console.print(f"[bold]{key}[/bold]: {value if value is not None else '—'}")


@world_app.command("nearby")
def world_nearby(
    kind: Annotated[Literal["barbarian", "player", "all"], typer.Option(help="Which villages to list.")] = "barbarian",
    radius: Annotated[int, typer.Option(min=1, max=100, help="Search radius in fields.")] = 15,
    limit: Annotated[int, typer.Option(min=1, max=500, help="Maximum rows.")] = 30,
    village_id: Annotated[int | None, typer.Option(help="Origin village ID (default: first own village).")] = None,
    as_json: JsonOption = False,
) -> None:
    """List villages around one of your villages, closest first."""
    from tribal_assistant.core.errors import DomainError
    from tribal_assistant.services.world import WorldService

    try:
        rows = _run(_with_session(lambda s: WorldService(s).nearby(village_id, kind, radius, limit)))
    except DomainError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    if as_json:
        _print_json(rows)
        return
    table = Table("Village", "Coords", "Points", "Distance", "Owner", "Spear", "Light cav.", "Farm")
    for n in rows:
        owner = "barbarian" if n.is_barbarian else f"{n.player_name or '?'}" + (f" [{n.ally_tag}]" if n.ally_tag else "")
        spear, light = n.travel_minutes.get("spear"), n.travel_minutes.get("light")
        table.add_row(
            n.name, n.coords, f"{n.points:,}", f"{n.distance:.1f}", owner,
            f"{spear:.0f} min" if spear is not None else "—",
            f"{light:.0f} min" if light is not None else "—",
            "yes" if n.is_farm_target else "",
        )
    console.print(table)


@agents_app.command("run")
def agents_run(
    dry_run: Annotated[
        bool | None, typer.Option("--dry-run/--live", help="Simulate or act in the game (default: AGENT_DRY_RUN).")
    ] = None,
    village: Annotated[list[int] | None, typer.Option(help="Only these village IDs (repeatable).")] = None,
    as_json: JsonOption = False,
) -> None:
    """Run every specialist once on each own village."""
    from dataclasses import asdict

    from tribal_assistant.agents.runner import AgentRunner
    from tribal_assistant.db.session import init_db

    async def _go():
        await init_db()
        try:
            return await AgentRunner(dry_run=dry_run, trigger="cli").run(village)
        finally:
            from tribal_assistant.client.session import game_session

            await game_session.close()

    report = _run(_go())
    if as_json:
        _print_json(asdict(report))
        return

    mode = "simulação" if report.dry_run else "ao vivo"
    console.print(f"[bold]rodada {report.run_id}[/bold] · cérebro {report.brain} · {mode}")
    if report.error:
        console.print(f"[red]{report.error}[/red]")
        raise typer.Exit(1)

    for village_run in report.villages:
        table = Table("Agente", "Resumo", title=village_run.village, show_lines=True)
        for key, summary in village_run.summaries.items():
            table.add_row(key, summary)
        console.print(table)


@agents_app.command("log")
def agents_log(
    limit: Annotated[int, typer.Option(min=1, max=500, help="Rows to show.")] = 30,
    village_id: Annotated[int | None, typer.Option(help="Filter by village ID.")] = None,
    as_json: JsonOption = False,
) -> None:
    """Show the latest agent decisions."""
    from tribal_assistant.repositories.agents import AgentRepository
    from tribal_assistant.schemas.agents import AgentDecisionOut

    rows = _run(_with_session(lambda s: AgentRepository(s).decisions(village_id=village_id, limit=limit)))
    decisions = [AgentDecisionOut.model_validate(r) for r in rows]
    if as_json:
        _print_json(decisions)
        return

    table = Table("Quando", "Agente", "Ação", "OK", "Resultado")
    for d in decisions:
        flag = "sim" if d.ok else "não"
        if d.dry_run:
            flag += " (sim.)"
        table.add_row(d.created_at.strftime("%d/%m %H:%M"), d.agent, d.action, flag, d.result[:90])
    console.print(table)


@agents_app.command("config")
def agents_config(as_json: JsonOption = False) -> None:
    """Show brain, provider and the runtime settings stored in the database."""
    from tribal_assistant.services.agents import AgentService

    config = _run(_with_session(lambda s: AgentService(s).config()))
    if as_json:
        _print_json(config)
        return

    brain = f"{config.provider} {config.model}" if config.brain == "llm" else "regras"
    console.print(f"cérebro: {brain} · última rodada agendada: {config.last_run_at or '—'}")

    table = Table("Configuração", "Valor")
    for key, value in config.settings.model_dump().items():
        table.add_row(key, str(value))
    console.print(table)


@agents_app.command("set")
def agents_set(
    values: Annotated[list[str], typer.Argument(help="key=value pairs, e.g. enabled=true interval_minutes=15.")],
) -> None:
    """Change agent settings at runtime; the running server picks them up on its next minute tick."""
    from pydantic import ValidationError

    from tribal_assistant.schemas.agent_settings import AgentSettingsUpdate
    from tribal_assistant.services.agents import AgentService

    pairs = {}
    for item in values:
        if "=" not in item:
            console.print(f"[red]use chave=valor: {item!r}[/red]")
            raise typer.Exit(1)
        key, value = item.split("=", 1)
        pairs[key.strip()] = value.strip()

    try:
        patch = AgentSettingsUpdate.model_validate(pairs)
    except ValidationError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    updated = _run(_with_session(lambda s: AgentService(s).update_settings(patch)))
    for key in pairs:
        console.print(f"{key} = {getattr(updated, key)}", style="green")


@app.command()
def quests(as_json: JsonOption = False) -> None:
    """Show active quests and pending rewards (as of the last agent round)."""
    from tribal_assistant.services.agents import AgentService

    data = _run(_with_session(lambda s: AgentService(s).quests()))
    if as_json:
        _print_json(data)
        return

    for quest in data.quests:
        status = "[green]pronta[/green]" if quest.can_complete else quest.state
        console.print(f"[bold]{quest.title}[/bold] ({quest.quest_id}) · {status}")
        for goal in quest.goals:
            progress = f"{goal.current}/{goal.target}" if goal.target is not None else ""
            console.print(f"  - {goal.title} {progress}")

    console.print(f"recompensas pendentes: {len(data.rewards)}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
