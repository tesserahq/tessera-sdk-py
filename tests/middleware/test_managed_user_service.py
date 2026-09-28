"""ManagedUserService: each middleware call is its own managed session."""

import warnings

import pytest
from sqlalchemy import String, create_engine, inspect, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from tessera_sdk.infra.database import DatabaseManager
from tessera_sdk.infra.service_factory import create_service_factory
from tessera_sdk.server.user_service import (
    ManagedUserService,
    create_managed_user_service_factory,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String)


@pytest.fixture
def manager(tmp_path) -> DatabaseManager:
    engine = create_engine(f"sqlite:///{tmp_path / 'users.db'}")
    Base.metadata.create_all(engine)
    db_manager = DatabaseManager(
        database_url=f"sqlite:///{tmp_path / 'unused.db'}", application_name="test"
    )
    db_manager.SessionLocal = sessionmaker(bind=engine)
    with db_manager.session_scope() as session:
        session.add(User(id="existing", email="existing@example.com"))
    return db_manager


def _get_user(session, user_id):
    return session.get(User, user_id)


def _onboard_user(session, data):
    user = User(id=data["id"], email=data["email"])
    session.add(user)
    session.flush()
    return user


def _service(manager) -> ManagedUserService:
    return create_managed_user_service_factory(
        manager, get_user=_get_user, onboard_user=_onboard_user
    )()


def test_get_user_returns_a_loaded_detached_user(manager):
    user = _service(manager).get_user_by_id_or_external_id("existing")

    assert inspect(user).detached
    assert user.email == "existing@example.com"


def test_get_user_returns_none_for_unknown_user(manager):
    assert _service(manager).get_user_by_id_or_external_id("missing") is None


def test_onboard_user_commits_and_returns_a_detached_user(manager):
    user = _service(manager).onboard_user({"id": "new", "email": "new@example.com"})

    assert inspect(user).detached
    assert user.email == "new@example.com"
    with manager.session_scope() as session:
        assert session.scalar(select(User.email).where(User.id == "new")) == (
            "new@example.com"
        )


def test_failed_onboarding_rolls_back(manager):
    def onboard_then_fail(session, data):
        _onboard_user(session, data)
        raise RuntimeError("welcome email failed")

    service = create_managed_user_service_factory(
        manager, get_user=_get_user, onboard_user=onboard_then_fail
    )()

    with pytest.raises(RuntimeError):
        service.onboard_user({"id": "partial", "email": "partial@example.com"})

    with manager.session_scope() as session:
        assert session.get(User, "partial") is None


def test_close_is_a_no_op(manager):
    _service(manager).close()


def test_create_service_factory_is_deprecated(manager):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        create_service_factory(object, manager)

    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
