"""Village timelapse: the pictures of each village in order, and each picture's bytes."""

from fastapi import APIRouter, Response

from tribal_assistant.api.deps import TimelapseServiceDep
from tribal_assistant.core.schemas.timelapse import FrameOut

IMAGE_CACHE = "private, max-age=31536000, immutable"

timelapse_router = APIRouter()


@timelapse_router.get("/villages/{village_id}/frames", response_model=list[FrameOut])
async def frames(village_id: int, service: TimelapseServiceDep) -> list[FrameOut]:
    return await service.frames(village_id)


@timelapse_router.get(
    "/frames/{frame_id}.jpg",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}, "description": "Foto da aldeia em JPEG"}},
)
async def frame_image(frame_id: int, service: TimelapseServiceDep) -> Response:
    image = await service.image(frame_id)
    return Response(content=image, media_type="image/jpeg", headers={"Cache-Control": IMAGE_CACHE})
