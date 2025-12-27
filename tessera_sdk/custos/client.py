"""
Main Custos client for interacting with the Custos API.
"""

import logging
from typing import Optional
import requests

from ..base.client import BaseClient
from ..constants import HTTPMethods
from .schemas.authorize_request import AuthorizeRequest
from .schemas.authorize_response import AuthorizeResponse
from .schemas.binding_request import CreateBindingRequest, DeleteBindingRequest
from .schemas.binding_response import BindingResponse
from .exceptions import (
    CustosError,
    CustosClientError,
    CustosServerError,
    CustosAuthenticationError,
    CustosNotFoundError,
    CustosValidationError,
)

logger = logging.getLogger(__name__)


class CustosClient(BaseClient):
    """
    A client for interacting with the Custos API.

    This client provides methods for authorization.
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
        Initialize the Custos client.

        Args:
            base_url: The base URL of the Custos API (e.g., "https://custos-api.yourdomain.com")
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
            service_name="custos",
        )

    def _handle_custos_exceptions(self, e: Exception):
        """Convert base exceptions to Custos-specific exceptions."""
        from ..base.exceptions import (
            TesseraAuthenticationError,
            TesseraNotFoundError,
            TesseraValidationError,
            TesseraClientError,
            TesseraServerError,
            TesseraError,
        )

        if isinstance(e, TesseraAuthenticationError):
            raise CustosAuthenticationError(str(e), e.status_code)
        elif isinstance(e, TesseraNotFoundError):
            raise CustosNotFoundError(str(e), e.status_code)
        elif isinstance(e, TesseraValidationError):
            raise CustosValidationError(str(e), e.status_code)
        elif isinstance(e, TesseraClientError):
            raise CustosClientError(str(e), e.status_code)
        elif isinstance(e, TesseraServerError):
            raise CustosServerError(str(e), e.status_code)
        elif isinstance(e, TesseraError):
            raise CustosError(str(e), e.status_code)
        else:
            raise e

    def authorize(
        self,
        user_id: str,
        action: str,
        resource: str,
        domain: str,
    ) -> AuthorizeResponse:
        """
        Authorize a user action on a resource.

        Args:
            user_id: User identifier
            action: Action to authorize (e.g., 'create', 'read', 'update', 'delete')
            resource: Resource type to authorize (e.g., 'account', 'document')
            domain: Domain identifier (e.g., 'account:1234')

        Returns:
            AuthorizeResponse object containing the authorization result

        Raises:
            CustosValidationError: If request data is invalid
            CustosAuthenticationError: If authentication fails
            CustosServerError: If the server encounters an error

        Example:
            >>> client = CustosClient(base_url="https://custos.example.com", api_token="your-token")
            >>> response = client.authorize(
            ...     user_id="4321",
            ...     action="create",
            ...     resource="account",
            ...     domain="account:1234"
            ... )
            >>> print(response.authorized)  # True or False
        """
        endpoint = "/authorization/authorize"

        request = AuthorizeRequest(
            user_id=user_id,
            action=action,
            resource=resource,
            domain=domain,
        )

        try:
            response = self._make_request(
                HTTPMethods.POST, endpoint, data=request.model_dump()
            )
            return AuthorizeResponse(**response.json())
        except Exception as e:
            self._handle_custos_exceptions(e)
            raise  # This should never be reached as _handle_custos_exceptions always raises

    def create_binding(
        self,
        role_identifier: str,
        user_id: str,
        domain: str,
        domain_metadata: Optional[dict] = None,
    ) -> BindingResponse:
        """
        Create a binding for a role.

        Args:
            role_identifier: Role UUID or slug
            user_id: User identifier to bind to the role
            domain: Domain identifier for the binding

        Returns:
            BindingResponse object containing the created binding information

        Raises:
            CustosValidationError: If request data is invalid
            CustosAuthenticationError: If authentication fails
            CustosServerError: If the server encounters an error

        Example:
            >>> client = CustosClient(base_url="https://custos.example.com", api_token="your-token")
            >>> response = client.create_binding(
            ...     role_identifier="role-uuid-123",
            ...     user_id="user-456",
            ...     domain="account:1234"
            ... )
            >>> print(response.binding_id)
        """
        endpoint = f"/roles/{role_identifier}/bindings"

        request = CreateBindingRequest(
            user_id=user_id,
            domain=domain,
            domain_metadata=domain_metadata or {},
        )

        try:
            response = self._make_request(
                HTTPMethods.POST, endpoint, data=request.model_dump()
            )
            return BindingResponse(**response.json())
        except Exception as e:
            self._handle_custos_exceptions(e)
            raise  # This should never be reached as _handle_custos_exceptions always raises

    def delete_binding(
        self,
        role_identifier: str,
        user_id: str,
        domain: str,
    ) -> None:
        """
        Delete a binding for a role.

        Args:
            role_identifier: Role UUID or slug
            user_id: User identifier to unbind from the role
            domain: Domain identifier for the binding

        Raises:
            CustosValidationError: If request data is invalid
            CustosAuthenticationError: If authentication fails
            CustosNotFoundError: If the binding is not found
            CustosServerError: If the server encounters an error

        Example:
            >>> client = CustosClient(base_url="https://custos.example.com", api_token="your-token")
            >>> client.delete_binding(
            ...     role_identifier="role-uuid-123",
            ...     user_id="user-456",
            ...     domain="account:1234"
            ... )
        """
        endpoint = f"/roles/{role_identifier}/bindings"

        request = DeleteBindingRequest(
            user_id=user_id,
            domain=domain,
        )

        try:
            self._make_request(
                HTTPMethods.DELETE,
                endpoint,
                data=request.model_dump(),
            )
        except Exception as e:
            self._handle_custos_exceptions(e)
            raise  # This should never be reached as _handle_custos_exceptions always raises
