"""Contract tests for managed sessions: session_scope, on_commit, savepoint."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from tessera_sdk.infra.database import DatabaseManager
from tessera_sdk.infra.transactions import (
    bind_session,
    current_session,
    on_commit,
    savepoint,
)


def make_session() -> Session:
    return Session(create_engine("sqlite://"))


@pytest.fixture
def manager(tmp_path) -> DatabaseManager:
    """A DatabaseManager whose sessions use SQLite.

    The engine DatabaseManager builds is lazy and never connects; its session
    factory is repointed at SQLite so the managed-session code runs as-is.
    """
    db_manager = DatabaseManager(
        database_url=f"sqlite:///{tmp_path / 'unused.db'}", application_name="test"
    )
    db_manager.SessionLocal = sessionmaker(bind=create_engine("sqlite://"))
    return db_manager


def test_autoflush_defaults_off_and_is_configurable(tmp_path):
    url = f"sqlite:///{tmp_path / 'unused.db'}"
    assert DatabaseManager(url, "test").SessionLocal.kw["autoflush"] is False
    assert (
        DatabaseManager(url, "test", autoflush=True).SessionLocal.kw["autoflush"]
        is True
    )


def test_on_commit_runs_callbacks_in_registration_order():
    session = make_session()
    calls = []

    on_commit(lambda: calls.append("first"), session=session)
    on_commit(lambda: calls.append("second"), session=session)
    session.execute(text("SELECT 1"))
    session.commit()

    assert calls == ["first", "second"]


def test_on_commit_outside_a_managed_scope_runs_immediately():
    calls = []

    on_commit(lambda: calls.append("now"))

    assert calls == ["now"]


def test_root_rollback_discards_on_commit_callbacks():
    session = make_session()
    calls = []

    on_commit(lambda: calls.append("called"), session=session)
    session.execute(text("SELECT 1"))
    session.rollback()
    session.commit()

    assert calls == []


def test_failed_savepoint_discards_only_its_callbacks():
    session = make_session()
    calls = []
    on_commit(lambda: calls.append("outer"), session=session)

    with pytest.raises(ValueError), savepoint(session):
        on_commit(lambda: calls.append("inner"), session=session)
        raise ValueError("invalid item")

    session.commit()

    assert calls == ["outer"]


def test_released_savepoint_does_not_run_callbacks_early():
    session = make_session()
    calls = []

    with savepoint(session):
        on_commit(lambda: calls.append("inner"), session=session)
    assert calls == []

    session.commit()
    assert calls == ["inner"]


def test_callback_failure_does_not_stop_later_callbacks():
    session = make_session()
    calls = []

    def fail():
        raise RuntimeError("callback failed")

    on_commit(fail, session=session)
    on_commit(lambda: calls.append("after failure"), session=session)
    session.execute(text("SELECT 1"))
    session.commit()

    assert calls == ["after failure"]


def test_early_commit_runs_only_callbacks_registered_before_it():
    session = make_session()
    calls = []

    on_commit(lambda: calls.append("phase 1"), session=session)
    session.execute(text("SELECT 1"))
    session.commit()
    on_commit(lambda: calls.append("phase 2"), session=session)
    assert calls == ["phase 1"]

    session.execute(text("SELECT 1"))
    session.commit()
    assert calls == ["phase 1", "phase 2"]


def test_session_scope_binds_the_current_session(manager):
    assert current_session() is None

    with manager.session_scope() as session:
        assert current_session() is session

    assert current_session() is None


def test_session_scope_defers_callbacks_until_commit(manager):
    calls = []

    with manager.session_scope() as session:
        on_commit(lambda: calls.append("committed"))
        session.execute(text("SELECT 1"))
        assert calls == []

    assert calls == ["committed"]


def test_session_scope_rollback_discards_callbacks(manager):
    calls = []

    with pytest.raises(ValueError), manager.session_scope() as session:
        on_commit(lambda: calls.append("called"))
        session.execute(text("SELECT 1"))
        raise ValueError("command failed")

    assert calls == []
    assert current_session() is None


def test_callbacks_run_without_an_active_session(manager):
    """Work scheduled by a hook must not register on the committed session."""
    seen = []

    with manager.session_scope() as session:
        on_commit(lambda: seen.append(current_session()))
        session.execute(text("SELECT 1"))

    assert seen == [None]


def test_bind_session_restores_the_previous_session():
    outer, inner = make_session(), make_session()

    with bind_session(outer):
        with bind_session(inner):
            assert current_session() is inner
        assert current_session() is outer
    assert current_session() is None
