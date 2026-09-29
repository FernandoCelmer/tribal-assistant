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
    help="Tribal Wars account assistant: sync, agents, world data and web dashboard.",
    no_args_is_help=True,
    add_completion=False,
)
world_app = typer.Typer(help="Public world data: sync, status, nearby villages.", no_args_is_help=True)
agents_app = typer.Typer(help="Village agents: run a round, read decisions and configuration.", no_args_is_help=True)
app.add_typer(world_app, name="world")
app.add_typer(agents_app, name="agents")
accounts_app = typer.Typer(help="Game accounts: list, add, enable or remove.", no_args_is_help=True)
db_app = typer.Typer(help="Database: copy the old single-account data into PostgreSQL or a new file.", no_args_is_help=True)
app.add_typer(accounts_app, name="accounts")
app.add_typer(db_app, name="db")

SELECTED_ACCOUNT: dict[str, int | None] = {"id": None}

JsonOption = Annotated[bool, typer.Option("--json", help="Print raw JSON instead of a table.")]


def _run[T](coro: Awaitable[T]) -> T:
    return asyncio.run(coro)  # type: ignore[arg-type]


async def _with_session[T](fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    from tribal_assistant.core.db.session import SessionFactory, init_db

    await init_db()
    async with SessionFactory() as session:
        account = await _account(session)
        if account is None:
            return await fn(session)

        from tribal_assistant.core.accounts.context import use_account

        with use_account(account):
            return await fn(session)


async def _account(session: AsyncSession):
    from tribal_assistant.core.accounts.registry import AccountRegistry

    return await AccountRegistry(session).find(SELECTED_ACCOUNT["id"])


async def _with_game[T](fn: Callable[[], Awaitable[T]]) -> T:
    """Run a browser-backed action and always release the Playwright session."""
    from tribal_assistant.core.accounts.context import use_account
    from tribal_assistant.core.db.session import SessionFactory, init_db
    from tribal_assistant.core.game.session import game_session

    await init_db()
    async with SessionFactory() as session:
        account = await _account(session)

    if account is None:
        raise typer.BadParameter("nenhuma conta cadastrada: use `tribal-assistant accounts add`")

    with use_account(account):
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
    account: Annotated[int | None, typer.Option("--account", "-a", help="Account id (default: the first enabled).")] = None,
) -> None:
    SELECTED_ACCOUNT["id"] = account
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
        "tribal_assistant.api.app:app", host=host, port=port, reload=reload, timeout_graceful_shutdown=5
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
    from tribal_assistant.core.services.assistant import AssistantService

    result = _run(_with_game(AssistantService().sync))
    console.print(result.message, style="green" if result.ok else "red")
    if not result.ok:
        raise typer.Exit(1)


@app.command()
def status(as_json: JsonOption = False) -> None:
    """Show the last synced account state (player and villages)."""
    from tribal_assistant.core.services.game import GameService

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


@world_app.command("sync")
def world_sync() -> None:
    """Download the public world data (villages, players, tribes, config)."""
    from tribal_assistant.core.db.session import init_db
    from tribal_assistant.core.game.modules.world_sync import sync_world

    async def _sync() -> None:
        await init_db()
        await sync_world()

    _run(_sync())
    console.print("world data synced", style="green")


@world_app.command("status")
def world_status(as_json: JsonOption = False) -> None:
    """Show what world data is stored locally."""
    from tribal_assistant.core.services.world import WorldService

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
    from tribal_assistant.core.services.world import WorldService

    try:
        rows = _run(_with_session(lambda s: WorldService(s).nearby(village_id, kind, radius, limit)))
    except DomainError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    if as_json:
        _print_json(rows)
        return
    table = Table("Village", "Coords", "Points", "Distance", "Owner", "Spear", "Light cav.")
    for n in rows:
        owner = "barbarian" if n.is_barbarian else f"{n.player_name or '?'}" + (f" [{n.ally_tag}]" if n.ally_tag else "")
        spear, light = n.travel_minutes.get("spear"), n.travel_minutes.get("light")
        table.add_row(
            n.name, n.coords, f"{n.points:,}", f"{n.distance:.1f}", owner,
            f"{spear:.0f} min" if spear is not None else "—",
            f"{light:.0f} min" if light is not None else "—",
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

    from tribal_assistant.core.agents.runner import AgentRunner
    from tribal_assistant.core.db.session import init_db

    async def _go():
        await init_db()
        try:
            return await AgentRunner(dry_run=dry_run, trigger="cli").run(village)
        finally:
            from tribal_assistant.core.game.session import game_session

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
    from tribal_assistant.core.repositories.agents import AgentRepository
    from tribal_assistant.core.schemas.agents import AgentDecisionOut

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
    from tribal_assistant.core.services.agents import AgentService

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

    from tribal_assistant.core.schemas.agent_settings import AgentSettingsUpdate
    from tribal_assistant.core.services.agents import AgentService

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
    from tribal_assistant.core.services.agents import AgentService

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


@accounts_app.command("list")
def accounts_list() -> None:
    """Every account with world, login and whether it plays."""
    from tribal_assistant.core.db.session import SessionFactory, init_db
    from tribal_assistant.core.repositories.accounts import AccountRepository

    async def run():
        await init_db()
        async with SessionFactory() as session:
            return await AccountRepository(session).list()

    table = Table("id", "nome", "mundo", "usuário", "ativa")
    for a in _run(run()):
        table.add_row(str(a.id), a.name, a.server, a.username, "sim" if a.enabled else "não")
    console.print(table)


@accounts_app.command("add")
def accounts_add(
    world_url: Annotated[str, typer.Option(help="World URL, e.g. https://br145.tribalwars.com.br")],
    username: Annotated[str, typer.Option(help="Game login.")],
    password: Annotated[str, typer.Option(prompt=True, hide_input=True, help="Game password (stored encrypted).")],
    name: Annotated[str | None, typer.Option(help="Label shown in the dashboard.")] = None,
    headless: Annotated[bool, typer.Option(help="Run this account's browser without a window.")] = False,
) -> None:
    """Add a game account; its password is encrypted with APP_SECRET or storage/secret.key."""
    from tribal_assistant.core.accounts.registry import AccountRegistry
    from tribal_assistant.core.db.session import SessionFactory, init_db

    server = world_url.split("//", 1)[-1].split(".", 1)[0]

    async def run():
        await init_db()
        async with SessionFactory() as session:
            return await AccountRegistry(session).create(name or f"{username} ({server})", server, world_url, username, password, headless)

    account = _run(run())
    console.print(f"conta {account.id} criada: {account.name}")


@accounts_app.command("enable")
def accounts_enable(account_id: int, enabled: Annotated[bool, typer.Option("--on/--off")] = True) -> None:
    """Turn an account's automatic play on or off."""
    from tribal_assistant.core.db.session import SessionFactory, init_db
    from tribal_assistant.core.repositories.accounts import AccountRepository

    async def run():
        await init_db()
        async with SessionFactory() as session:
            repo = AccountRepository(session)
            account = await repo.get(account_id)
            if account is None:
                raise typer.BadParameter(f"conta {account_id} não existe")
            account.enabled = enabled
            await repo.save(account)

    _run(run())
    console.print(f"conta {account_id} {'ativada' if enabled else 'desativada'}")


@db_app.command("copy")
def db_copy(
    target: Annotated[str, typer.Option(help="Target URL, e.g. postgresql+asyncpg://user:pass@host:5432/tribal")],
    source: Annotated[str, typer.Option(help="Source URL (default: the old SQLite file).")] = "sqlite+aiosqlite:///./storage/tw.db",
    wipe: Annotated[bool, typer.Option(help="Drop and recreate every table on the target first.")] = False,
) -> None:
    """Copy all data into the multi-account schema; old rows go to account 1 (created from .env)."""
    from tribal_assistant.core.db.migrate import DatabaseCopier

    report = DatabaseCopier(source, target).run(wipe=wipe)
    table = Table("tabela", "linhas")
    for name, count in report.tables.items():
        table.add_row(name, str(count))
    console.print(table)
    if report.skipped:
        console.print(f"sem dados na origem: {', '.join(report.skipped)}")
    console.print("Pronto. Coloque DATABASE_URL com o destino no .env e suba o servidor.")
