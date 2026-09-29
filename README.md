# tribal-assistant

FastAPI control plane + Playwright worker para automação Tribal Wars.

Arquitetura em camadas: **api → services → repositories → models** (SQLAlchemy async). Cliente de navegador isolado em `app/client/`. Scheduler `APScheduler` roda jobs recorrentes dentro do processo FastAPI.

## Setup

```bash
cd /Users/fernandocelmer/Lab/FernandoCelmer/tribal-assistant
make install
cp .env.example .env
# edite .env com credenciais TW
make migrate      # opcional; init_db() cria tabelas no primeiro boot
```

## Rodar

```bash
make run
# API em http://localhost:8000
# Swagger em http://localhost:8000/docs
```

## Testes

```bash
make test
make lint
make typecheck
```

## Estrutura

```
app/
├── __init__.py               factory create_app() + lifespan
├── cli.py                    uvicorn entrypoint
├── api/
│   ├── health.py
│   └── v1/
│       ├── routers.py        agrega v1
│       ├── villages.py
│       ├── farm.py
│       └── assistant.py
├── core/
│   ├── config.py             pydantic-settings
│   ├── errors.py             DomainError + handlers
│   └── logging.py            loguru bootstrap
├── db/
│   ├── base.py               Base + TimestampMixin
│   └── session.py            async engine + SessionFactory + init_db
├── models/                   SQLAlchemy ORM
│   ├── village.py
│   ├── building.py
│   ├── unit.py
│   ├── report.py
│   ├── farm_target.py
│   └── incoming_attack.py
├── schemas/                  Pydantic IO
│   ├── health.py
│   ├── village.py
│   ├── farm.py
│   └── assistant.py
├── repositories/             DB access
│   ├── villages.py
│   └── farm.py
├── services/                 domain logic
│   ├── villages.py
│   ├── farm.py
│   └── assistant.py
├── client/                   browser automation
│   ├── browser.py            Playwright wrapper + session state
│   ├── human.py              delays humanos
│   ├── login.py              login + world select
│   ├── scraper/
│   │   └── village.py        HTML → dataclass (pure)
│   └── modules/
│       ├── village_sync.py   scrape + upsert
│       └── farm.py           FarmRunner
└── scheduler/
    ├── runtime.py            singleton AsyncIOScheduler
    └── jobs.py               registrar jobs (sync/farm)

alembic/                      migrations
tests/
├── conftest.py               engine in-memory + AsyncClient override
├── api/                      HTTP smoke
└── services/                 lógica pura
```

## Endpoints

| Método | Rota                       | Uso                                    |
|--------|----------------------------|----------------------------------------|
| GET    | /health                    | health check                           |
| GET    | /api/v1/villages           | lista aldeias                          |
| POST   | /api/v1/villages           | upsert por coords                      |
| GET    | /api/v1/villages/{id}      | detalhe                                |
| PATCH  | /api/v1/villages/{id}      | atualiza recursos/pop                  |
| GET    | /api/v1/farm/targets       | lista alvos                            |
| POST   | /api/v1/farm/targets       | adiciona alvo                          |
| POST   | /api/v1/farm/tick          | executa uma rodada de saque            |
| GET    | /api/v1/assistant/status   | scheduler + login                      |
| POST   | /api/v1/assistant/start    | inicia scheduler                       |
| POST   | /api/v1/assistant/stop     | pausa scheduler                        |
| POST   | /api/v1/assistant/sync     | sincroniza conta agora                 |
| GET    | /api/v1/game/overview      | jogador, aldeias, tropas, comandos, relatórios, recomendações |
| GET    | /api/v1/world/status       | dados públicos do mundo                |
| GET    | /api/v1/world/nearby       | aldeias próximas (bárbaras/jogadores)  |

## Migrations

```bash
make revision m="add x"
make migrate
```
