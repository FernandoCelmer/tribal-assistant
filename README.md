# Tribal Assistant — Tribal Wars assistant, CLI and web dashboard

[![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-browser-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-FE5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/en/v1.0.0/)

**Tribal Assistant** is an open-source Python assistant for the browser strategy game **Tribal Wars** (Guerra Tribal / Die Stämme). It syncs your account through a real browser session, stores villages, resources, troops, buildings, commands and reports in a local database, recommends what to build next, finds barbarian villages to farm, and shows everything in a medieval-themed web dashboard with light and dark mode.

Use it three ways: as a **CLI** (`tribal-assistant`), as a **Python library** (`import tribal_assistant`), or as a **FastAPI server** with a dashboard.

| Light | Dark |
|-------|------|
| ![Tribal Assistant dashboard, light theme](docs/screenshots/dashboard-light.png) | ![Tribal Assistant dashboard, dark theme](docs/screenshots/dashboard-dark.png) |

## Features

- **Account sync** — player, points, ranking, villages, resources and production, storage, population, troops, recruitment queue, buildings, incoming and outgoing commands, battle reports.
- **Build advisor** — ranks the next building upgrades by priority, cost and time until resources are available.
- **Farm assistant** — farm targets with templates A/B/C, wall level tracking and scheduled farm ticks.
- **World data** — downloads the public world files and lists nearby barbarian or player villages with travel times per unit.
- **Scavenging** — shows each scavenge option, its return time and unlock state.
- **Incoming attack alerts** — highlights attacks and nobles heading to your villages.
- **Scheduler** — APScheduler jobs with jitter and configurable quiet hours.
- **Dashboard** — responsive web UI, keyboard accessible, light/dark theme, component docs at `/design`.
- **REST API** — FastAPI with OpenAPI docs at `/docs`.

## Install

```bash
pip install git+https://github.com/FernandoCelmer/tribal-assistant.git
playwright install chromium
```

From a clone:

```bash
git clone https://github.com/FernandoCelmer/tribal-assistant.git
cd tribal-assistant
poetry install --extras dev   # or: make install
playwright install chromium
cp .env.example .env          # add your world URL and credentials
```

## Configuration

Settings come from environment variables or `.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `TW_WORLD_URL` | — | World URL, e.g. `https://br144.tribalwars.com.br` |
| `TW_USERNAME` / `TW_PASSWORD` | — | Game login |
| `TW_SERVER` | `brxx` | World code |
| `DATABASE_URL` | `sqlite+aiosqlite:///./storage/tw.db` | SQLite or PostgreSQL (asyncpg) |
| `HEADLESS` | `false` | Run Chromium without a window |
| `SYNC_INTERVAL_SECONDS` | `120` | Account sync interval |
| `QUIET_HOURS` | empty | Pause syncing, e.g. `23:30-07:00` |
| `FARM_ENABLED` | `true` | Enable farm ticks |

See [.env.example](.env.example) for the full list.

## CLI

```bash
tribal-assistant --help
tribal-assistant serve                      # API + dashboard + scheduler on :8000
tribal-assistant sync                       # sync the account now
tribal-assistant status                     # player, villages, incoming attacks
tribal-assistant status --json

tribal-assistant world sync                 # download public world data
tribal-assistant world status
tribal-assistant world nearby --radius 20 --kind barbarian

tribal-assistant farm list --all
tribal-assistant farm add "512|488" --template B --wall 1
tribal-assistant farm remove 3
tribal-assistant farm tick
```

`python -m tribal_assistant` works too.

## Library

```python
import asyncio

from tribal_assistant.db.session import SessionFactory, init_db
from tribal_assistant.services.game import GameService
from tribal_assistant.services.world import WorldService


async def main() -> None:
    await init_db()
    async with SessionFactory() as session:
        overview = await GameService(session).overview()
        for village in overview.villages:
            print(village.name, village.coords, village.wood, village.clay, village.iron)

        nearby = await WorldService(session).nearby(None, kind="barbarian", radius=15, limit=10)
        for target in nearby:
            print(target.coords, target.distance, target.travel_minutes.get("light"))


asyncio.run(main())
```

The FastAPI app is `tribal_assistant.server:app`; build your own with `tribal_assistant.server.create_app()`.

## Web dashboard and API

```bash
tribal-assistant serve
```

- Dashboard: <http://localhost:8000/>
- Component docs: <http://localhost:8000/design>
- OpenAPI docs: <http://localhost:8000/docs>

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/health` | Health check |
| GET | `/api/v1/assistant/status` | Scheduler and login state |
| POST | `/api/v1/assistant/start` · `/stop` · `/sync` | Control the assistant |
| GET | `/api/v1/game/overview` | Player, villages, troops, commands, reports, recommendations |
| GET | `/api/v1/world/status` | Stored world data |
| GET | `/api/v1/world/nearby` | Nearby barbarian or player villages |
| GET · POST | `/api/v1/farm/targets` | List or add farm targets |
| POST | `/api/v1/farm/tick` | Run one farm round |
| GET · POST · PATCH | `/api/v1/villages` | Village records |

## Architecture

```
tribal_assistant/
├── cli.py            Typer CLI
├── server.py         FastAPI factory, lifespan, dashboard routes
├── api/              HTTP routers (v1)
├── services/         domain logic: game, world, farm, advisor, assistant
├── repositories/     SQLAlchemy async data access
├── models/           ORM models
├── schemas/          Pydantic input/output
├── client/           Playwright session, login, scrapers, sync modules
├── scheduler/        APScheduler runtime and jobs
├── db/               engine, session factory, init_db
└── web/              dashboard (HTML, CSS design system, icons)
```

Layers: `api → services → repositories → models`. Scrapers are pure functions (HTML in, data out) and are tested with saved fixtures.

## Development

```bash
make test        # pytest
make lint        # ruff
make typecheck   # mypy
make migrate     # alembic upgrade head
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## Disclaimer

Tribal Assistant is an unofficial project and is not affiliated with InnoGames. Automating actions may break the game rules of your server; you are responsible for how you use it. Try it on a test account first.
