"""Request-scoped dependencies: the account being worked on, a database session and core services."""

from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.accounts.context import use_account
from tribal_assistant.core.accounts.registry import AccountRegistry
from tribal_assistant.core.db.session import SessionFactory
from tribal_assistant.core.services.accounts import AccountService
from tribal_assistant.core.services.agents import AgentService
from tribal_assistant.core.services.assistant import AssistantService
from tribal_assistant.core.services.challenges import ChallengeService
from tribal_assistant.core.services.docs import DocsService
from tribal_assistant.core.services.forecast import ForecastService
from tribal_assistant.core.services.game import GameService
from tribal_assistant.core.services.knobs import KnobService
from tribal_assistant.core.services.live import LiveGameService
from tribal_assistant.core.services.observability import ObservabilityService
from tribal_assistant.core.services.reports import ReportService
from tribal_assistant.core.services.timelapse import TimelapseService
from tribal_assistant.core.services.world import WorldService

ACCOUNT_COOKIE = "tw_account"
_providers: dict[type, Callable] = {}


def requested_account(request: Request) -> int | None:
    raw = (
        request.query_params.get("account")
        or request.headers.get("x-account")
        or request.cookies.get(ACCOUNT_COOKIE)
    )
    return int(raw) if raw and raw.isdigit() else None


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        account = await AccountRegistry(session).find(requested_account(request))
        if account is None:
            yield session
            return

        with use_account(account):
            yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def provide[S](service: type[S]) -> Callable[..., S]:
    """FastAPI dependency that builds a core service around the request's session."""
    if service not in _providers:

        def build(session: SessionDep) -> S:
            return service(session)

        build.__name__ = f"provide_{service.__name__}"
        _providers[service] = build

    return _providers[service]


AccountServiceDep = Annotated[AccountService, Depends(provide(AccountService))]
AgentServiceDep = Annotated[AgentService, Depends(provide(AgentService))]
AssistantServiceDep = Annotated[AssistantService, Depends(provide(AssistantService))]
ChallengeServiceDep = Annotated[ChallengeService, Depends(provide(ChallengeService))]
DocsServiceDep = Annotated[DocsService, Depends(provide(DocsService))]
GameServiceDep = Annotated[GameService, Depends(provide(GameService))]
ObservabilityServiceDep = Annotated[ObservabilityService, Depends(provide(ObservabilityService))]
WorldServiceDep = Annotated[WorldService, Depends(provide(WorldService))]
ForecastServiceDep = Annotated[ForecastService, Depends(provide(ForecastService))]
LiveGameServiceDep = Annotated[LiveGameService, Depends(provide(LiveGameService))]
ReportServiceDep = Annotated[ReportService, Depends(provide(ReportService))]
KnobServiceDep = Annotated[KnobService, Depends(provide(KnobService))]
TimelapseServiceDep = Annotated[TimelapseService, Depends(provide(TimelapseService))]
