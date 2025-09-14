"""
Service factory for creating service instances with database sessions from request state.
"""

from typing import Any
from starlette.requests import Request


class ServiceFactory:
    """
    Factory for creating service instances that can access the database session
    from the request state.
    """

    def __init__(self, service_class: type):
        self.service_class = service_class

    def __call__(self, request: Request) -> Any:
        """
        Create a service instance using the database session from request state.

        Args:
            request: The FastAPI request object

        Returns:
            Service instance with the database session from request state
        """
        db_session = getattr(request.state, "db_session", None)
        if not db_session:
            raise RuntimeError("No database session found in request state")

        return self.service_class(db=db_session)


def create_service_factory(service_class: type) -> ServiceFactory:
    """
    Create a service factory for the given service class.

    Args:
        service_class: The service class to create a factory for

    Returns:
        ServiceFactory instance
    """
    return ServiceFactory(service_class)
