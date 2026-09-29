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

from tribal_assistant import __version__
from tribal_assistant.core.config import settings

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
app.add_typer(world_app, name="world")

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

    uvicorn.run("tribal_assistant.server:app", host=host, port=port, reload=reload)


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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
