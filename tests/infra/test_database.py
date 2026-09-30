"""DatabaseManager builds a PostgreSQL engine with the driver the SDK ships."""

import pytest
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from tessera_sdk.infra.database import DatabaseManager

DATABASE_URL = "postgresql://user:pass@localhost:5432/app"


@pytest.fixture
def uninstrumented():
    # The instrumentor is a process-wide singleton; start and end clean.
    SQLAlchemyInstrumentor().uninstrument()
    yield
    SQLAlchemyInstrumentor().uninstrument()


def test_plain_postgresql_url_uses_psycopg3_driver():
    db_manager = DatabaseManager(database_url=DATABASE_URL, application_name="test")

    assert db_manager.engine.dialect.driver == "psycopg"


def test_engine_is_instrumented_for_tracing(uninstrumented):
    db_manager = DatabaseManager(database_url=DATABASE_URL, application_name="test")

    assert db_manager.engine.dispatch.before_cursor_execute
