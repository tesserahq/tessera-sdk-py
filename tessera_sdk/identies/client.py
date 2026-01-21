"""
Main Identies client for interacting with the Identies API.
"""

import logging
from typing import Optional
import requests

from ..base.client import BaseClient
from ..constants import HTTPMethods
from .schemas.introspect_response import IntrospectResponse
from .schemas.user_response import UserResponse

logger = logging.getLogger(__name__)


class IdentiesClient(BaseClient):
    """
    A client for interacting with the Identies API.

    This client provides methods for managing clients and assets through the Vaulta API.
    """

    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the Identies client.

        Args:
            base_url: The base URL of the Identies API (e.g., "https://identies-api.yourdomain.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            session: Optional requests.Session instance to use
        """
        super().__init__(
            base_url=base_url,
            api_token=api_token,
            timeout=timeout,
            session=session,
            service_name="identies",
        )

    # User Management Methods

    def userinfo(self) -> UserResponse:
        """
        Get the user info.

        Args:
            None

        Returns:
            UserInfo object
        """
        response = self._make_request(HTTPMethods.GET, "/userinfo")
        return UserResponse(**response.json())

    def get_user(self, user_id: Optional[str] = None) -> UserResponse:
        """
        Get a user.

        Args:
            user_id: Optional ID of the user to retrieve. If omitted, returns
                the user associated with the current token.

        Returns:
            UserResponse object

        Raises:
            IdentiesNotFoundError: If client is not found
        """
        endpoint = f"/users/{user_id}" if user_id else "/user"
        response = self._make_request(HTTPMethods.GET, endpoint)
        return UserResponse(**response.json())

    def get_internal_user(self, user_id: str) -> UserResponse:
        """
        Get an internal user.

        Args:
            user_id: ID of the user to retrieve.

        Returns:
            UserResponse object

        Raises:
            IdentiesNotFoundError: If client is not found
        """
        endpoint = f"/internal/users/{user_id}"
        response = self._make_request(HTTPMethods.GET, endpoint)
        return UserResponse(**response.json())

    def introspect(self) -> IntrospectResponse:
        """
        Introspect a token.

        Args:
            None

        Returns:
            IntrospectResponse object

        Raises:
            IdentiesNotFoundError: If client is not found
        """
        response = self._make_request(HTTPMethods.POST, "/api-keys/introspect")
        return IntrospectResponse(**response.json())
