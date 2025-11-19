"""
Service factory for creating service instances with database sessions from request state.
"""

from typing import Any
from starlette.requests import Request
from tessera_sdk.core.database_manager import DatabaseManager


class ServiceFactory:
    """
    Factory for creating service instances that can access the database session
    from the request state.
    """

    def __init__(self, service_class: type, db_manager: DatabaseManager):
        self.service_class = service_class
        self.db_manager = db_manager

    def __call__(self) -> Any:
        """
        Create a service instance using the database session from request state.

        Returns:
            Service instance with the database session from request state
        """
        db_session = self.db_manager.create_session()
        if not db_session:
            raise RuntimeError("No database session found in request state")

        return self.service_class(db=db_session)


def create_service_factory(service_class: type, db_manager: DatabaseManager) -> ServiceFactory:
    """
    Create a service factory for the given service class.

    Args:
        service_class: The service class to create a factory for
        db_manager: The database manager to use

    Returns:
        ServiceFactory instance
    """
    return ServiceFactory(service_class, db_manager)
