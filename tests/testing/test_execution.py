import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Integer, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from tessera_sdk.infra.transactions import current_session, on_commit
from tessera_sdk.server.dependencies import create_db_dependency
from tessera_sdk.testing import execution_boundary, managed_db_override


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'items.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_execution_boundary_commits_and_defers_callbacks(session):
    calls = []

    with execution_boundary(session):
        assert current_session() is session
        session.add(Item(id=1))
        on_commit(lambda: calls.append("after commit"))
        assert calls == []

    assert calls == ["after commit"]
    assert session.scalar(select(Item.id)) == 1


def test_execution_boundary_rolls_back_only_the_code_under_test(session):
    session.add(Item(id=1))  # staged "fixture" data

    with pytest.raises(RuntimeError), execution_boundary(session):
        session.add(Item(id=2))
        session.flush()
        raise RuntimeError("failed after staging")

    assert session.scalars(select(Item.id)).all() == [1]


def test_managed_db_override_matches_the_production_contract(session, tmp_path):
    from tessera_sdk.infra.database import DatabaseManager

    manager = DatabaseManager(f"sqlite:///{tmp_path / 'unused.db'}", "test")
    get_db, DbSession = create_db_dependency(manager)
    app = FastAPI()
    calls = []

    @app.post("/items")
    async def create(db: DbSession):
        assert current_session() is db
        db.add(Item(id=7))
        on_commit(lambda: calls.append("dispatched"))
        return {"ok": True}

    app.dependency_overrides[get_db] = managed_db_override(session)

    assert TestClient(app).post("/items").json() == {"ok": True}
    assert calls == ["dispatched"]
    assert session.scalar(select(Item.id)) == 7
