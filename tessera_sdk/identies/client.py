"""
Main Identies client for interacting with the Identies API.
"""

import logging
from typing import Any, Optional
import requests

from ..base.client import BaseClient
from ..constants import HTTPMethods
from .schemas.external_account_response import (
    CheckResponse,
    ExternalAccountPageResponse,
    ExternalAccountResponse,
    LinkTokenResponse,
)
from .schemas.introspect_response import IntrospectResponse
from .schemas.user_response import UserResponse
from ..config import get_settings

logger = logging.getLogger(__name__)


class IdentiesClient(BaseClient):
    """
    A client for interacting with the Identies API.

    This client provides methods for managing clients and assets through the Vaulta API.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
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
            base_url=base_url or get_settings().identies_api_url,
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

    # External Accounts Methods

    def create_link_token(
        self,
        platform: str,
        external_user_id: str,
        data: Optional[dict[str, Any]] = None,
        expires_in_seconds: int = 600,
    ) -> LinkTokenResponse:
        """
        Create a short-lived, single-use link token.

        Intended for backend/webhook use (e.g. external platform creates token
        when user starts linking). Protect this endpoint at network or with
        API key if needed.

        Args:
            platform: External platform (e.g. telegram).
            external_user_id: External platform user id.
            data: Optional payload to store with the linked account.
            expires_in_seconds: Token TTL in seconds; default 10 minutes.

        Returns:
            LinkTokenResponse with token and expires_at.
        """
        body: dict[str, Any] = {
            "platform": platform,
            "external_user_id": external_user_id,
        }
        if data is not None:
            body["data"] = data
        if expires_in_seconds != 600:
            body["expires_in_seconds"] = expires_in_seconds
        response = self._make_request(
            HTTPMethods.POST,
            "/external-accounts/link-tokens",
            data=body,
        )
        return LinkTokenResponse(**response.json())

    def list_external_accounts(
        self,
        platform: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> ExternalAccountPageResponse:
        """
        List external accounts for the current user (paginated).

        Args:
            platform: Optional filter by platform (e.g. telegram).
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            ExternalAccountPageResponse with items, total, page, size, pages.
        """
        params: dict[str, int | str] = {"page": page, "size": size}
        if platform is not None:
            params["platform"] = platform
        response = self._make_request(
            HTTPMethods.GET,
            "/external-accounts",
            params=params,
        )
        return ExternalAccountPageResponse(**response.json())

    def list_user_external_accounts(
        self,
        user_id: str,
        platform: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> ExternalAccountPageResponse:
        """
        List external accounts for a specific user (paginated).

        Args:
            user_id: ID of the user whose external accounts to list.
            platform: Optional filter by platform (e.g. telegram).
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            ExternalAccountPageResponse with items, total, page, size, pages.
        """
        params: dict[str, int | str] = {"page": page, "size": size}
        if platform is not None:
            params["platform"] = platform
        response = self._make_request(
            HTTPMethods.GET,
            f"/users/{user_id}/external-accounts",
            params=params,
        )
        return ExternalAccountPageResponse(**response.json())

    def check_external_account(self, platform: str, external_id: str) -> CheckResponse:
        """
        Check if an external account (platform + external_id) is linked to a user.

        Args:
            platform: External platform (e.g. telegram).
            external_id: External platform user id.

        Returns:
            CheckResponse with linked status, user, and external_accounts when found.
        """
        response = self._make_request(
            HTTPMethods.POST,
            "/external-accounts/check",
            data={"platform": platform, "external_id": external_id},
        )
        return CheckResponse(**response.json())

    def link_external_account(self, token: str) -> ExternalAccountResponse:
        """
        Link the current user to the external account referenced by the token.

        Args:
            token: The short-lived link token from the external platform.

        Returns:
            ExternalAccountResponse for the linked account.
        """
        response = self._make_request(
            HTTPMethods.POST,
            "/external-accounts/link",
            data={"token": token},
        )
        return ExternalAccountResponse(**response.json())

    def delete_external_account(self, external_account_id: str) -> None:
        """
        Unlink an external account. Only the owner can delete.

        Args:
            external_account_id: UUID of the external account to delete.
        """
        self._make_request(
            HTTPMethods.DELETE,
            f"/external-accounts/{external_account_id}",
        )
