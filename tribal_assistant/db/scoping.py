"""Rows that belong to one account or one world, filtered automatically by the current account."""

from sqlalchemy import ForeignKey, Integer, String, event
from sqlalchemy.orm import (
    Mapped,
    ORMExecuteState,
    Session,
    declared_attr,
    mapped_column,
    with_loader_criteria,
)

from tribal_assistant.accounts.context import current_account_id, current_world


class AccountScoped:
    @declared_attr
    def account_id(cls) -> Mapped[int]:  # noqa: N805
        return mapped_column(Integer, ForeignKey("accounts.id"), index=True, nullable=False)


class WorldScoped:
    @declared_attr
    def world(cls) -> Mapped[str]:  # noqa: N805
        return mapped_column(String(32), primary_key=True)


@event.listens_for(Session, "do_orm_execute")
def _scope_queries(state: ORMExecuteState) -> None:
    if state.execution_options.get("all_accounts") or not (state.is_select or state.is_update or state.is_delete):
        return

    account_id = current_account_id()
    world = current_world()
    options = []

    if account_id is not None:
        options.append(with_loader_criteria(AccountScoped, lambda cls: cls.account_id == account_id, include_aliases=True))

    if world is not None:
        options.append(with_loader_criteria(WorldScoped, lambda cls: cls.world == world, include_aliases=True))

    if options:
        state.statement = state.statement.options(*options)


@event.listens_for(Session, "before_flush")
def _stamp_new_rows(session: Session, flush_context: object, instances: object) -> None:
    account_id = current_account_id()
    world = current_world()

    for obj in session.new:
        if isinstance(obj, AccountScoped) and getattr(obj, "account_id", None) is None and account_id is not None:
            obj.account_id = account_id

        if isinstance(obj, WorldScoped) and getattr(obj, "world", None) is None and world is not None:
            obj.world = world
