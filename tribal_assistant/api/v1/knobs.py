"""Self-tuning parameter endpoints: list, tune now, manual override."""

from fastapi import APIRouter

from tribal_assistant.api.deps import KnobServiceDep
from tribal_assistant.core.schemas.knobs import KnobIn, KnobOut, KnobTuneOut

knobs_router = APIRouter()


@knobs_router.get("", response_model=list[KnobOut])
async def knobs(service: KnobServiceDep) -> list[KnobOut]:
    return await service.list()


@knobs_router.post("/tune", response_model=KnobTuneOut)
async def tune(service: KnobServiceDep) -> KnobTuneOut:
    return await service.tune_now()


@knobs_router.put("/{name}", response_model=KnobOut)
async def set_knob(name: str, body: KnobIn, service: KnobServiceDep) -> KnobOut:
    return await service.set(name, body)
