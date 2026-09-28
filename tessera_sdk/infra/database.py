"""
Database manager class for SQLAlchemy setup and session management.

This class encapsulates database engine creation, session management,
and event listeners. It can be easily moved to a common package.
"""

from collections.abc import Generator, Iterator
from contextlib import contextmanager

from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
)
from sqlalchemy.orm.session import Session as SessionType

from .transactions import bind_session


class DatabaseManager:
    """
    Manages SQLAlchemy database engine, sessions, and event listeners.

    This class can be easily moved to a common package by accepting
    configuration as parameters instead of importing app-specific modules.
    """

    def __init__(
        self,
        database_url: str,
        application_name: str,
        pool_size: int = 10,
        max_overflow: int = 5,
        pool_pre_ping: bool = True,
        pool_recycle: int = 300,
        pool_use_lifo: bool = True,
        autoflush: bool = False,
    ):
        """
        Initialize the database manager.

        Args:
            database_url: Database connection URL
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
            pool_pre_ping: Test connections before using them
            pool_recycle: Connection recycle time in seconds
            pool_use_lifo: Use LIFO for connection pool
            application_name: Application name for database connections
            autoflush: Flush pending changes before each query (SQLAlchemy's
                default). Services adopting managed transactions
                (``session_scope``) pass ``True``; the default stays
                ``False`` for backward compatibility and will change once
                every service has migrated.
        """
        self.database_url = database_url
        self.application_name = application_name

        # Create engine
        self.engine = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            pool_recycle=pool_recycle,
            pool_use_lifo=pool_use_lifo,
            connect_args={"application_name": application_name},
        )
        SQLAlchemyInstrumentor().instrument(
            engine=self.engine,
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=autoflush, bind=self.engine
        )

    def get_db(self) -> Generator[SessionType, None, None]:
        """
        FastAPI dependency for getting a database session.

        Yields:
            Database session
        """
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_session(self) -> SessionType:
        """
        Create a new database session.

        Returns:
            New database session
        """
        return self.SessionLocal()

    def dispose(self):
        """Dispose of the database engine and close all connections."""
        self.engine.dispose()

    @contextmanager
    def db_session(self):
        """Context manager: commit on success, rollback on exception, always close."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def session_scope(self) -> Iterator[SessionType]:
        """One managed session for one application execution.

        Commits when the block succeeds, rolls back when an exception escapes,
        and closes. While the block runs the session is the current session,
        so ``on_commit`` callbacks registered anywhere inside it run only
        after the commit. Use this, not ``get_db``/``create_session``, for
        every entry point (tasks, CLI, tool calls, event handlers); FastAPI
        routes use ``create_db_dependency``.
        """
        with self.db_session() as session, bind_session(session):
            yield session
