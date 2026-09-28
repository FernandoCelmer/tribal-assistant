.PHONY: install venv playwright run test lint typecheck migrate revision fmt

VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

venv:
	python3.12 -m venv $(VENV)

install: venv
	$(PIP) install -e ".[dev]"
	$(VENV)/bin/playwright install chromium

run:
	$(VENV)/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000

test:
	$(VENV)/bin/pytest -v

lint:
	$(VENV)/bin/ruff check app tests

fmt:
	$(VENV)/bin/ruff format app tests
	$(VENV)/bin/ruff check --fix app tests

typecheck:
	$(VENV)/bin/mypy app

migrate:
	$(VENV)/bin/alembic upgrade head

revision:
	$(VENV)/bin/alembic revision --autogenerate -m "$(m)"
