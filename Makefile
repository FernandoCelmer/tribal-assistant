.PHONY: install venv playwright run test lint typecheck fmt web web-install web-types web-check

VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

venv:
	python3.12 -m venv $(VENV)

install: venv
	$(PIP) install -e ".[dev]"
	$(VENV)/bin/playwright install chromium

run:
	$(VENV)/bin/uvicorn tribal_assistant.api.app:app --reload --host 0.0.0.0 --port 8000

test:
	$(VENV)/bin/pytest -v

lint:
	$(VENV)/bin/ruff check tribal_assistant tests

fmt:
	$(VENV)/bin/ruff format tribal_assistant tests
	$(VENV)/bin/ruff check --fix tribal_assistant tests

typecheck:
	$(VENV)/bin/mypy tribal_assistant

web-install:
	cd apps/web && npm install

web:
	cd apps/web && npm run dev

web-types:
	cd apps/web && npm run api:types

web-check:
	cd apps/web && npm run check
