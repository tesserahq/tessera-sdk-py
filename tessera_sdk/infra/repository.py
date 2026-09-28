"""Shared persistence mechanics for concrete repositories."""

from typing import Any, ClassVar, TypeVar

from sqlalchemy.engine import Result
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable

ScalarT = TypeVar("ScalarT")


class Repository:
    """Base for repositories that run inside a managed session.

    Repositories query, stage, and flush when they need generated state; they
    never commit, roll back, or close the session. The execution boundary
    (``DatabaseManager.session_scope`` or the FastAPI dependency) owns the
    transaction.

    Set-based ORM UPDATE and DELETE statements bypass normal attribute
    assignment, so SQLAlchemy must reconcile their effects with objects already
    loaded in the Session identity map. All set-based mutations go through the
    two helpers below. ``synchronize_session="fetch"`` identifies the affected
    rows (using ``RETURNING`` on PostgreSQL) and refreshes or expires only the
    matching loaded objects. Callers cannot choose another policy:
    ``synchronize_session=False`` leaves loaded entities stale, and
    ``expire_all()`` is too broad a repair.
    """

    _MUTATION_OPTIONS: ClassVar[dict[str, str]] = {"synchronize_session": "fetch"}

    def __init__(self, db: Session):
        self.db = db

    def _execute_mutation(self, statement: Executable) -> Result[Any]:
        """Execute synchronized set-based ORM DML and return its full result."""
        return self.db.execute(statement, execution_options=self._MUTATION_OPTIONS)

    def _scalar_mutation(self, statement: Executable) -> ScalarT | None:
        """Execute synchronized ORM DML and return its first RETURNING value."""
        return self.db.scalar(statement, execution_options=self._MUTATION_OPTIONS)
