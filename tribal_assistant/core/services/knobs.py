"""Self-tuning decision parameters: list them, tune them now or set one by hand."""

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knobs import Knobs, KnobStore, Tuner
from tribal_assistant.core.errors import NotFoundError, ValidationError
from tribal_assistant.core.schemas.knobs import KnobIn, KnobOut, KnobTuneChange, KnobTuneOut

MANUAL = "ajuste manual"


class KnobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.store = KnobStore(session)

    async def list(self) -> list[KnobOut]:
        items = []
        for row in await self.store.rows():
            spec = Knobs.SPECS[row["name"]]
            items.append(KnobOut(**row, share=spec.share, integer=spec.integer))
        return items

    async def tune_now(self) -> KnobTuneOut:
        changes = await Tuner(self.session).run()
        return KnobTuneOut(changes=[KnobTuneChange(name=name, value=value, reason=why) for name, value, why in changes])

    async def set(self, name: str, body: KnobIn) -> KnobOut:
        spec = Knobs.SPECS.get(name)
        if spec is None:
            raise NotFoundError(f"parâmetro {name!r} não existe")

        value = body.value
        if value <= 0:
            raise ValidationError("o valor precisa ser maior que zero", field="value")
        if spec.share and value > 1:
            raise ValidationError("fração precisa ficar entre 0 e 1", field="value")
        if spec.integer:
            value = float(round(value))

        await self.store.set(name, value, MANUAL)
        await self.session.commit()
        return next(item for item in await self.list() if item.name == name)
