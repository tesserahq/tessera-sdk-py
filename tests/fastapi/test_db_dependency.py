"""create_db_dependency: one managed session per request, committed before the
response is sent."""

from contextlib import contextmanager
from typing import Annotated
from unittest.mock import patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tessera_sdk.infra.database import DatabaseManager
from tessera_sdk.infra.transactions import current_session, on_commit
from tessera_sdk.server.dependencies import create_db_dependency


def make_manager(tmp_path) -> DatabaseManager:
    db_manager = DatabaseManager(
        database_url=f"sqlite:///{tmp_path / 'unused.db'}", application_name="test"
    )
    db_manager.SessionLocal = sessionmaker(bind=create_engine("sqlite://"))
    return db_manager


def test_route_sees_the_request_session_as_current(tmp_path):
    _get_db, DbSession = create_db_dependency(make_manager(tmp_path))
    app = FastAPI()

    @app.get("/same")
    async def same(session: DbSession):
        return {"same": current_session() is session}

    assert TestClient(app).get("/same").json() == {"same": True}


def test_route_and_its_dependencies_share_one_session(tmp_path):
    db_manager = make_manager(tmp_path)
    _get_db, DbSession = create_db_dependency(db_manager)
    app = FastAPI()
    opened = []
    session_factory = db_manager.SessionLocal

    def counting_factory():
        session = session_factory()
        opened.append(session)
        return session

    db_manager.SessionLocal = counting_factory

    def load_entity(session: DbSession):
        return session

    @app.get("/entity")
    async def read(
        session: DbSession, entity_session: Annotated[Session, Depends(load_entity)]
    ):
        return {"same": entity_session is session}

    assert TestClient(app).get("/entity").json() == {"same": True}
    assert len(opened) == 1


def test_callbacks_run_after_the_request_commits(tmp_path):
    _get_db, DbSession = create_db_dependency(make_manager(tmp_path))
    app = FastAPI()
    calls = []

    @app.post("/write")
    async def write(session: DbSession):
        on_commit(lambda: calls.append("dispatched"))
        return {"dispatched_before_commit": bool(calls)}

    response = TestClient(app).post("/write")

    assert response.json() == {"dispatched_before_commit": False}
    assert calls == ["dispatched"]


def test_commit_failure_is_reported_before_the_response_is_sent(tmp_path):
    db_manager = make_manager(tmp_path)
    _get_db, DbSession = create_db_dependency(db_manager)
    app = FastAPI()

    @app.post("/write")
    def write(_session: DbSession):
        return {"status": "accepted"}

    @contextmanager
    def failing_scope():
        session = Session(create_engine("sqlite://"))
        try:
            yield session
            raise RuntimeError("commit failed")
        finally:
            session.close()

    with patch.object(db_manager, "db_session", failing_scope):
        response = TestClient(app, raise_server_exceptions=False).post("/write")

    assert response.status_code == 500


def test_get_db_can_be_overridden(tmp_path):
    get_db, DbSession = create_db_dependency(make_manager(tmp_path))
    app = FastAPI()
    replacement = Session(create_engine("sqlite://"))

    @app.get("/which")
    async def which(session: DbSession):
        return {"replaced": session is replacement}

    async def override():
        yield replacement

    app.dependency_overrides[get_db] = override

    assert TestClient(app).get("/which").json() == {"replaced": True}
