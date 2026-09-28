"""User service for the authentication/onboarding middlewares with managed
sessions.

``AuthenticationMiddleware`` and ``UserOnboardingMiddleware`` build a user
service from a factory, call one method, then close it. Handing them a raw
session (``create_service_factory``) leaves the transaction without an owner:
nothing commits on success or rolls back on failure. The factory built here
runs each call as its own managed execution (``DatabaseManager.session_scope``)
and returns a fully loaded, detached user, which is what the middlewares store
on ``request.state.user``.

Usage::

    user_service_factory = create_managed_user_service_factory(
        db_manager,
        get_user=lambda db, user_id: UserRepository(db).get_user_by_id_or_external_id(user_id),
        onboard_user=lambda db, data: OnboardCommand(db).execute(data),
    )
    app.add_middleware(UserOnboardingMiddleware, user_service_factory=user_service_factory)
    app.add_middleware(
        AuthenticationMiddleware,
        skip_paths=SKIP_PATHS,
        user_service_factory=user_service_factory,
    )
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from tessera_sdk.infra.database import DatabaseManager

GetUser = Callable[[Session, str], Any]
OnboardUser = Callable[[Session, Any], Any]


def _detach(session: Session, user: Any) -> Any:
    if user is not None:
        # Load every column before detaching: the scope's commit would
        # otherwise leave expired attributes that cannot be reloaded.
        session.refresh(user)
        session.expunge(user)
    return user


class ManagedUserService:
    """The user-service interface the SDK middlewares expect."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        *,
        get_user: GetUser,
        onboard_user: OnboardUser,
    ):
        self._db_manager = db_manager
        self._get_user = get_user
        self._onboard_user = onboard_user

    def get_user_by_id_or_external_id(self, user_id: str) -> Any:
        with self._db_manager.session_scope() as session:
            return _detach(session, self._get_user(session, user_id))

    def onboard_user(self, user_data: Any) -> Any:
        with self._db_manager.session_scope() as session:
            return _detach(session, self._onboard_user(session, user_data))

    def close(self) -> None:
        """Called by the middlewares; each method already completed its scope."""


def create_managed_user_service_factory(
    db_manager: DatabaseManager,
    *,
    get_user: GetUser,
    onboard_user: OnboardUser,
) -> Callable[[], ManagedUserService]:
    """Factory for ``user_service_factory=`` on the SDK middlewares."""
    service = ManagedUserService(
        db_manager, get_user=get_user, onboard_user=onboard_user
    )
    return lambda: service
