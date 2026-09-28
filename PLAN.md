# tribal-wars-bot — Plano Completo

Bot automação Tribal Wars 24/7. Objetivo: dominar mundo via farm, build, recrutamento e conquista automatizados, com humano só em decisões estratégicas.

---

## 1. Visão geral

Bot roda navegador headless, mantém sessão viva, sincroniza estado do jogo em banco local, executa ações (farm, construir, recrutar, atacar, defender) via fila de jobs agendados. Dashboard web pra monitorar e sobrepor decisões.

**Não-metas MVP:** IA de estratégia global, coordenação multi-conta, PvP inteligente contra players ativos.

---

## 2. Stack

| Camada | Tech | Motivo |
|--------|------|--------|
| Automação browser | Playwright (Python async) | Contorna anti-bot melhor que Selenium; suporta cookies persistentes |
| Parser HTML | BeautifulSoup4 + lxml | Rápido e simples |
| Config | pydantic-settings | Type-safe env |
| Log | loguru | Zero-config, rotate |
| Persistência | SQLite (MVP) → PostgreSQL (prod) | Zero deps local |
| Scheduler | APScheduler | Cron + intervals no processo |
| Fila | Redis + RQ (fase 2) | Timing crítico ataques |
| API | FastAPI (fase 3) | Dashboard control |
| Frontend | Next.js (fase 4, opcional) | UI mapa + status |
| Deploy | Docker Compose | VPS single-node |
| Notificações | Telegram bot API | Alertas críticos |

---

## 3. Arquitetura

```
tribal-wars-bot/
├── bot/
│   ├── config.py         # env + settings
│   ├── browser.py        # playwright wrapper + session persist
│   ├── human.py          # delays humanos + jitter
│   ├── login.py          # login + world select
│   ├── scraper/
│   │   ├── village.py    # overview, recursos, pop
│   │   ├── buildings.py  # niveis, fila
│   │   ├── units.py      # tropas em casa/fora
│   │   ├── reports.py    # relatorios ataque
│   │   ├── map.py        # aldeias barbaras/players ao redor
│   │   └── incoming.py   # ataques recebidos
│   ├── modules/
│   │   ├── farm.py       # assistente saque barbaras
│   │   ├── builder.py    # fila construcao
│   │   ├── recruiter.py  # fila recrutamento
│   │   ├── defense.py    # detect incoming + dodge/snipe
│   │   ├── nobleman.py   # conquista (fase mid/late)
│   │   └── scout.py      # explorador auto
│   ├── scheduler.py      # APScheduler jobs
│   ├── db/
│   │   ├── models.py     # SQLModel
│   │   └── session.py
│   ├── notify/
│   │   └── telegram.py
│   └── main.py           # entrypoint
├── api/                  # FastAPI (fase 3)
├── web/                  # Next.js (fase 4)
├── tests/
├── docker-compose.yml    # fase 3
├── pyproject.toml
├── .env.example
├── README.md
└── PLAN.md               # este arquivo
```

---

## 4. Módulos core

### 4.1 Browser (`bot/browser.py`)
- Chromium headed em dev, headless em prod
- `storage_state` persistido em JSON → sessão sobrevive restart
- User-agent fixo desktop
- Locale pt-BR

### 4.2 Login (`bot/login.py`)
- Detecta form login. Se ausente = sessão ativa
- Submete credenciais
- Seleciona mundo pelo `TW_SERVER`
- Se captcha: pausa 60s pra resolver manual → salva state

### 4.3 Scraper (`bot/scraper/`)
- Cada tela do jogo tem um scraper puro (HTML in, dataclass out)
- Zero side-effects, testável
- `village.py`: recursos, pop, coords, nome
- `buildings.py`: níveis atuais + fila (posição, tempo restante)
- `units.py`: tropas próprias, em trânsito, apoiando
- `reports.py`: lê `/game.php?screen=report` — loot, perdas, muralha
- `map.py`: parse `/map.php` — grid aldeias (bárbaras, jogadores, tribos)
- `incoming.py`: overview screen — ataques chegando com timing

### 4.4 Farm (`bot/modules/farm.py`)
- Usa Assistente de Saque (`screen=am_farm`)
- Configura templates A/B/C: A leve (só saque), B médio, C limpeza (com axes)
- Ordena bárbaras por distância + último loot
- Envia round-robin respeitando tropas disponíveis
- Cooldown por alvo: espera relatório voltar
- Pausa se muralha detectada > threshold

### 4.5 Builder (`bot/modules/builder.py`)
- Fila infinita por aldeia
- Ordem prioridade config: eco early → militar mid → muralha late
- Templates: `early_eco`, `farm_village`, `noble_train`, `defensive`
- Checa recursos + slots fila antes enfileirar

### 4.6 Recruiter (`bot/modules/recruiter.py`)
- Mantém quartel/estábulo/oficina cheios
- Ratio config: `{spear: 0.5, sword: 0.3, axe: 0.2}` por aldeia
- Respeita cap população
- Reserva pop pra nobres se `noble_train=true`

### 4.7 Defense (`bot/modules/defense.py`)
- Poll overview a cada 30s durante alerta
- Detecta incoming: origem, tropa suspeita (nobre = flash), chegada
- Estratégias:
  - **Dodge**: envia tropas apoiar aldeia própria antes chegada
  - **Snipe**: envia lanceiro/cav timing ms entre chegadas nobres
  - **Stack**: solicita apoio tribo (fase 4)
- Alerta Telegram em todo incoming

### 4.8 Nobleman (`bot/modules/nobleman.py`)
- Rastreia moedas ouro/pacotes disponíveis
- Cunha nobres em aldeias-fábrica
- Planeja ataques conquista: 4 nobres + suporte 5-10k
- Timing chegadas em intervalo 100-500ms (evita snipe)

### 4.9 Scheduler (`bot/scheduler.py`)
- APScheduler AsyncIOScheduler
- Jobs recorrentes:
  - `sync_village` cada 5min
  - `sync_map` cada 30min
  - `sync_reports` cada 2min
  - `sync_incoming` cada 30s (ou 5s em alerta)
  - `farm_tick` cada 3-8min (jitter)
  - `builder_tick` cada 10min
  - `recruiter_tick` cada 10min
- Jobs one-shot: ataques agendados timing exato

### 4.10 Anti-detect
- Delay ações: `random.uniform(1200, 3800)ms`
- Pausa "sono": config `SLEEP_WINDOW=23:30-07:00` — reduz atividade
- Mouse move real (Playwright) antes clique
- Scroll aleatório overview
- Nunca 2 requests no mesmo ms

---

## 5. Persistência (schema mínimo)

```sql
villages(id, name, coords, is_own, wood, clay, iron, storage, pop_cur, pop_max, updated_at)
buildings(village_id, name, level, target_level, queued_until)
units(village_id, name, home, away, support_in, updated_at)
reports(id, when, origin_id, target_id, loot_wood, loot_clay, loot_iron, wall_level, defender_alive)
farm_targets(id, coords, last_attack_at, last_loot, wall_level, template)
attacks_outgoing(id, origin_id, target_id, arrival_at, units_json, kind)  -- farm|snipe|nobreza
attacks_incoming(id, origin_id, target_id, arrival_at, is_nobreza_guess)
map_villages(id, coords, name, player, tribe, points, is_barb)
```

---

## 6. Roadmap por fases

### Fase 0 — MVP local (**HOJE**)
- [x] Estrutura projeto
- [x] Browser + session persist
- [x] Login + world select
- [x] Scraper village (recursos + pop)
- [x] Main entrypoint
- [ ] **Validar login funciona** ← próximo passo do usuário

### Fase 1 — Farm assistant (semana 1)
- [ ] Scraper `map.py` — lista bárbaras em raio N
- [ ] Scraper `reports.py`
- [ ] Módulo farm com templates A/B/C
- [ ] SQLite + models
- [ ] Scheduler + `farm_tick`
- [ ] Testar 24h em conta descartável

### Fase 2 — Build + recruit (semana 2)
- [ ] Scraper `buildings.py`
- [ ] Builder queue infinita
- [ ] Recruiter ratio
- [ ] Templates eco/militar
- [ ] Telegram alertas erros

### Fase 3 — Defesa + multi-aldeia (semana 3-4)
- [ ] Scraper `incoming.py`
- [ ] Detecção ataques
- [ ] Alerta Telegram incoming
- [ ] Dodge auto
- [ ] Suporte multi-aldeia (loop cada uma)
- [ ] FastAPI dashboard básico (lista aldeias, status)

### Fase 4 — Conquista + coordenação (semana 5-6)
- [ ] Módulo nobleman
- [ ] Timing ataques ms
- [ ] Snipe detection
- [ ] Web UI mapa (Next.js)
- [ ] Coordenação apoio tribo (manual trigger, exec auto)

### Fase 5 — Deploy prod
- [ ] Docker Compose
- [ ] Postgres + Redis
- [ ] VPS Hostinger (usa skill hostinger)
- [ ] Rotação IP proxy (fase avançada)

---

## 7. Riscos + mitigação

| Risco | Mitigação |
|-------|-----------|
| Ban por bot | Conta descartável primeiro, delays humanos, sleep window, sem burst |
| Captcha | Pausa longa + notif Telegram pra resolver manual |
| HTML muda | Scrapers puros isolados, testes com fixtures HTML salvo |
| Timing errado ataques | NTP sync host, delay compensation medido |
| Session expira | Auto-relogin on 302 → login page |
| VPS cai | Systemd restart + healthcheck endpoint |

---

## 8. Comandos úteis

```bash
# Setup
cd /Users/fernandocelmer/Lab/FernandoCelmer/tribal-wars-bot
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
cp .env.example .env

# Rodar MVP
python -m bot.main

# Testes (quando existirem)
pytest tests/

# Ver navegador headless
HEADLESS=false python -m bot.main
```

---

## 9. Convenções código

- Python 3.12+
- `async/await` tudo IO
- Type hints obrigatório
- `loguru` log, nunca `print`
- Scrapers = funções puras (HTML → dataclass)
- Módulos = têm side-effects, usam scrapers + browser
- Zero comentários óbvios, só WHY não-trivial
- Commits: git-flow (`feature/ISSUE-N`, ícone+tipo)

---

## 10. Próximas ações concretas

1. Rodar `python -m bot.main` — validar login funciona
2. Ajustar seletores `bot/login.py` se HTML mudou
3. Confirmar `bot/scraper.py` lê recursos (log deve mostrar VillageStatus)
4. Se OK: começar Fase 1 (farm assistant)
5. Criar repo GitHub `FernandoCelmer/tribal-wars-bot`
6. Setup git-flow (develop branch, protected main)
