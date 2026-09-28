"""Test helpers that run code under a fixture session the way an entry point
(``DatabaseManager.session_scope`` / ``create_db_dependency``) does."""

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from tessera_sdk.infra.transactions import bind_session


@contextmanager
def execution_boundary(session: Session) -> Iterator[Session]:
    """Commit on success, roll back on error, with ``session`` as the current
    session so ``on_commit`` callbacks wait for the commit.

    Anything staged before entering is committed first, so a rollback only
    undoes the code under test. Pair it with a fixture session created with
    ``join_transaction_mode="create_savepoint"`` inside an outer transaction
    the fixture rolls back::

        with pytest.raises(ReminderError):
            with execution_boundary(db):
                CreateVehicleCommand(db).execute(data)
    """
    session.commit()
    with bind_session(session):
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def managed_db_override(session: Session) -> Callable[[], AsyncIterator[Session]]:
    """Replacement for the app's ``get_db`` in ``app.dependency_overrides``
    with the production contract, bound to a fixture session::

        app.dependency_overrides[get_db] = managed_db_override(db)
    """

    async def override_get_db() -> AsyncIterator[Session]:
        with bind_session(session):
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    return override_get_db
