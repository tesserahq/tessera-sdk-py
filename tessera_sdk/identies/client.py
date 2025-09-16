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
from .exceptions import (
    IdentiesError,
    IdentiesClientError,
    IdentiesServerError,
    IdentiesAuthenticationError,
    IdentiesNotFoundError,
    IdentiesValidationError,
)

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
        timeout: int = 30,
        max_retries: int = 3,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the Identies client.

        Args:
            base_url: The base URL of the Identies API (e.g., "https://identies-api.yourdomain.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            session: Optional requests.Session instance to use
        """
        super().__init__(
            base_url=base_url,
            api_token=api_token,
            timeout=timeout,
            max_retries=max_retries,
            session=session,
            service_name="identies"
        )

    def _handle_identies_exceptions(self, e: Exception):
        """Convert base exceptions to Identies-specific exceptions."""
        from ..base.exceptions import (
            TesseraAuthenticationError,
            TesseraNotFoundError,
            TesseraValidationError,
            TesseraClientError,
            TesseraServerError,
            TesseraError,
        )
        
        if isinstance(e, TesseraAuthenticationError):
            raise IdentiesAuthenticationError(str(e), e.status_code)
        elif isinstance(e, TesseraNotFoundError):
            raise IdentiesNotFoundError(str(e), e.status_code)
        elif isinstance(e, TesseraValidationError):
            raise IdentiesValidationError(str(e), e.status_code)
        elif isinstance(e, TesseraClientError):
            raise IdentiesClientError(str(e), e.status_code)
        elif isinstance(e, TesseraServerError):
            raise IdentiesServerError(str(e), e.status_code)
        elif isinstance(e, TesseraError):
            raise IdentiesError(str(e), e.status_code)
        else:
            raise e

    # User Management Methods

    def userinfo(self) -> UserResponse:
        """
        Get the user info.

        Args:
            None

        Returns:
            UserInfo object
        """
        try:
            response = self._make_request(HTTPMethods.GET, "/userinfo")
            return UserResponse(**response.json())
        except Exception as e:
            self._handle_identies_exceptions(e)

    def get_user(self) -> UserResponse:
        """
        Get a specific user.

        Args:
            None

        Returns:
            UserResponse object

        Raises:
            IdentiesNotFoundError: If client is not found
        """
        try:
            response = self._make_request(HTTPMethods.GET, "/user")
            return UserResponse(**response.json())
        except Exception as e:
            self._handle_identies_exceptions(e)

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
        try:
            response = self._make_request(HTTPMethods.POST, "/api-keys/introspect")
            return IntrospectResponse(**response.json())
        except Exception as e:
            self._handle_identies_exceptions(e)
