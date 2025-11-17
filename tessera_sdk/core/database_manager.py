"""
Database manager class for SQLAlchemy setup and session management.

This class encapsulates database engine creation, session management,
and event listeners. It can be easily moved to a common package.
"""

from typing import Optional, Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import (
    sessionmaker,
)
from sqlalchemy.orm.session import Session as SessionType


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
            enable_otel: Enable OpenTelemetry instrumentation
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

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
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
