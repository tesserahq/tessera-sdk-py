"""
Main Custos client for interacting with the Custos API.
"""

import logging
from typing import Optional
import requests

from .._base.client import BaseClient
from ...constants import HTTPMethods
from .schemas.authorize_request import AuthorizeRequest
from .schemas.authorize_response import AuthorizeResponse
from .schemas.membership_request import CreateMembershipRequest, DeleteMembershipRequest
from .schemas.membership_response import MembershipResponse

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
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the Custos client.

        Args:
            base_url: The base URL of the Custos API (e.g., "https://custos-api.yourdomain.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            session: Optional requests.Session instance to use
        """
        super().__init__(
            base_url=base_url,
            api_token=api_token,
            timeout=timeout,
            session=session,
            service_name="custos",
        )

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
        """
        endpoint = "/authorization/authorize"

        request = AuthorizeRequest(
            user_id=user_id,
            action=action,
            resource=resource,
            domain=domain,
        )

        response = self._make_request(
            HTTPMethods.POST, endpoint, data=request.model_dump()
        )
        return AuthorizeResponse(**response.json())

    def create_membership(
        self,
        role_identifier: str,
        user_id: str,
        domain: str,
        domain_metadata: Optional[dict] = None,
    ) -> MembershipResponse:
        """
        Create a membership for a role.
        """
        endpoint = f"/roles/{role_identifier}/memberships"

        request = CreateMembershipRequest(
            user_id=user_id,
            domain=domain,
            domain_metadata=domain_metadata or {},
        )

        response = self._make_request(
            HTTPMethods.POST, endpoint, data=request.model_dump()
        )
        return MembershipResponse(**response.json())

    def delete_membership(
        self,
        role_identifier: str,
        user_id: str,
        domain: str,
    ) -> None:
        """
        Delete a membership for a role.
        """
        endpoint = f"/roles/{role_identifier}/memberships"

        request = DeleteMembershipRequest(
            user_id=user_id,
            domain=domain,
        )

        self._make_request(
            HTTPMethods.DELETE,
            endpoint,
            data=request.model_dump(),
        )
