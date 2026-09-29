"""Challenges endpoint: the game's achievements and how the agents chase them."""

from fastapi import APIRouter

from tribal_assistant.api.deps import ChallengeServiceDep
from tribal_assistant.core.schemas.challenges import ChallengesOut

challenges_router = APIRouter()


@challenges_router.get("", response_model=ChallengesOut)
async def challenges(service: ChallengeServiceDep) -> ChallengesOut:
    return await service.list()
