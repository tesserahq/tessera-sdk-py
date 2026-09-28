"""FastAPI dependency that runs each request in one managed session."""

from collections.abc import AsyncIterator, Callable
from typing import Annotated, Any, TypeAlias

from fastapi import Depends
from sqlalchemy.orm import Session

from tessera_sdk.infra.database import DatabaseManager

GetDb: TypeAlias = Callable[[], AsyncIterator[Session]]


def create_db_dependency(db_manager: DatabaseManager) -> tuple[GetDb, Any]:
    """Build the request-session dependency for an application.

    Returns ``(get_db, DbSession)``. Define both once, at module level::

        get_db, DbSession = create_db_dependency(db_manager)

        @router.post("/things")
        def create_thing(payload: ThingCreate, db: DbSession): ...

    ``DbSession`` is ``Annotated[Session, Depends(get_db, scope="function")]``.
    The function scope is required: with FastAPI's default request scope the
    commit would run after the response has been sent, so a failed commit
    could follow a 2xx. Every route and dependency must use the same
    ``DbSession`` so FastAPI's dependency cache yields one session per
    request. Tests override ``get_db``.

    ``get_db`` is ``async`` so the current session it binds is visible to the
    route; a sync generator dependency would run in a threadpool context.
    """

    async def get_db() -> AsyncIterator[Session]:
        with db_manager.session_scope() as session:
            yield session

    db_session = Annotated[Session, Depends(get_db, scope="function")]
    return get_db, db_session
