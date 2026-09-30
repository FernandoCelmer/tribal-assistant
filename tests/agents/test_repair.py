import asyncio
from typing import Any

from tribal_assistant.core.agents.repair import ErrorRepair
from tribal_assistant.core.agents.tools.act import SendSpy


class Model(ErrorRepair):
    def __init__(self, reply: str | None) -> None:
        self.reply = reply
        self.asked = 0

    async def ask(self, system: str, prompt: str, purpose: str) -> str | None:
        self.asked += 1
        return self.reply


def fix(model: Model, error: str, arguments: dict[str, Any] | None = None) -> dict[str, Any] | None:
    return asyncio.run(model.fix(SendSpy(), arguments or {"target": "500|500", "count": 1, "reason": "sondar"}, error, {}))


def test_reads_the_error_and_returns_corrected_arguments():
    model = Model('```json\n{"target": "500|500", "count": 5}\n```')

    assert fix(model, "Cada ataque precisa de pelo menos 10 de população.") == {"target": "500|500", "count": 5, "reason": "sondar"}


def test_errors_arguments_cannot_fix_never_reach_the_model():
    model = Model('{"target": "500|500", "count": 5}')

    for error in ("faltam 100 wood", "RECUSADO: fora do raio", "Paladino deve ter pelo menos o nível 8.", "limite de ataques por hora"):
        assert fix(model, error) is None
    assert model.asked == 0


def test_answers_outside_the_schema_or_unchanged_are_dropped():
    assert fix(Model('{"alvo": "1|1"}'), "erro estranho") is None
    assert fix(Model("null"), "erro estranho") is None
    assert fix(Model("não sei"), "erro estranho") is None
    assert fix(Model('{"target": "500|500", "count": 1, "reason": "sondar"}'), "erro estranho") is None


def test_state_errors_are_not_argument_errors():
    model = Model('{"target": "500|500", "count": 5}')

    for error in ("coleta 2 não está livre para enviar", "só há 0 spy em casa", "fila de construção não mudou"):
        assert fix(model, error) is None
    assert model.asked == 0
