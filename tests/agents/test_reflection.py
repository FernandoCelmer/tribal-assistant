from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.reflection import Belief, Reflection

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def belief(expect: str = "down", baseline: float = 0.6, confidence: float = 0.5) -> Belief:
    return Belief("belief:x", "madeira trava a fila", "subir bosque", "idle_queue", expect, baseline, confidence, NOW.isoformat(), NOW.isoformat())


class Writer:
    def __init__(self, reply: str) -> None:
        self.reply = reply

    async def ask(self, system: str, prompt: str, purpose: str) -> str:
        return self.reply


def test_the_measure_confirms_or_contradicts_a_belief() -> None:
    assert belief().verdict(0.3, 0.05) == 1
    assert belief().verdict(0.9, 0.05) == -1
    assert belief().verdict(0.61, 0.05) == 0
    assert belief("up", baseline=2).verdict(5, 0.05) == 1


def test_an_unchecked_belief_fades() -> None:
    assert belief(confidence=0.8).decayed(NOW + timedelta(hours=24), 24) == 0.4


def test_the_model_reply_is_read_leniently() -> None:
    reply = 'Aqui: [{"conclusao": "a", "medida": "idle_queue", "espera": "cair"}] fim'

    assert Reflection.parse(reply)[0]["conclusao"] == "a"
    assert Reflection.parse("sem json") == []


async def test_reflection_stores_beliefs_tied_to_a_known_measure(session: AsyncSession) -> None:
    reply = (
        '[{"conclusao": "madeira trava a fila", "acao": "subir bosque", "medida": "idle_queue", "espera": "cair"},'
        ' {"conclusao": "inventada", "medida": "sorte", "espera": "subir"}]'
    )
    notes = await Reflection(session, Writer(reply)).run(force=True)

    assert notes == ["nova: madeira trava a fila"]
    stored = await Reflection(session).beliefs()
    assert [b.measure for b in stored] == ["idle_queue"]
    assert "50% madeira trava a fila → subir bosque" in await Reflection(session).summary()


async def test_a_contradicted_belief_loses_confidence_and_is_dropped(session: AsyncSession) -> None:
    old = (NOW - timedelta(hours=5)).isoformat()
    weak = Belief("belief:y", "x", "y", "idle_queue", "down", 0.0, 0.25, old, datetime.now(UTC).isoformat())
    reflection = Reflection(session, Writer("[]"))

    notes = await reflection.verify([weak], {"idle_queue": 0.8}, Knobs())

    assert notes == ["contrariada: x", "descartada: x"]
    await session.commit()
    assert await reflection.beliefs() == []
