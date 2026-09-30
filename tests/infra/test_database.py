"""DatabaseManager builds a PostgreSQL engine with the driver the SDK ships."""

from tessera_sdk.infra.database import DatabaseManager


def test_plain_postgresql_url_uses_psycopg3_driver():
    db_manager = DatabaseManager(
        database_url="postgresql://user:pass@localhost:5432/app",
        application_name="test",
    )

    assert db_manager.engine.dialect.driver == "psycopg"
