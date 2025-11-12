"""
Machine-to-Machine (M2M) token utility for obtaining access tokens from OAuth/OIDC providers.
"""

import asyncio
from typing import Optional, Dict, Any
import requests
import logging
from pydantic import BaseModel
from ..config import get_settings
from ..base.client import BaseClient
from ..constants import HTTPMethods


class M2MTokenRequest(BaseModel):
    """Request model for M2M token authentication."""

    client_id: str
    client_secret: str
    audience: str
    grant_type: str = "client_credentials"


class M2MTokenResponse(BaseModel):
    """Response model for M2M token authentication."""

    access_token: str
    token_type: str
    expires_in: int
    scope: Optional[str] = None


logger = logging.getLogger(__name__)


class M2MTokenClient(BaseClient):
    """Client for obtaining machine-to-machine tokens from OAuth/OIDC providers."""

    def __init__(
        self,
        provider_domain: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the M2M token client.

        Args:
            provider_domain: OAuth/OIDC provider domain (e.g., 'dev-si3yygt34d0fk7hc.us.auth0.com')
                           If not provided, will use settings.
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            session: Optional requests.Session instance to use
        """
        self.settings = get_settings()
        self.provider_domain = provider_domain or self.settings.oidc_domain
        if not self.provider_domain:
            raise ValueError(
                "Provider domain must be provided either as a parameter or via settings"
            )

        super().__init__(
            base_url=f"https://{self.provider_domain}",
            api_token=None,
            timeout=timeout,
            max_retries=max_retries,
            session=session,
            service_name="m2m-token",
        )

    def _prepare_token_request(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        audience: str = "",
    ) -> tuple[M2MTokenRequest, Dict[str, str]]:
        """
        Prepare the token request payload and headers.

        Args:
            client_id: The OAuth client ID
            client_secret: The OAuth client secret
            audience: The API audience (identifier)

        Returns:
            Tuple of (payload, headers)

        Raises:
            ValueError: If credentials are missing
        """
        # Use settings defaults if not provided
        client_id = client_id or self.settings.service_account_client_id
        client_secret = client_secret or self.settings.service_account_client_secret
        audience = audience or self.settings.oidc_api_audience

        if not client_id or not client_secret:
            raise ValueError(
                "Client ID and Client Secret must be provided either as parameters or via settings"
            )

        payload = M2MTokenRequest(
            client_id=client_id, client_secret=client_secret, audience=audience
        )

        headers = {"Content-Type": "application/json"}
        return payload, headers

    def _process_token_response(self, data: Dict[str, Any]) -> M2MTokenResponse:
        """
        Process and validate the token response.

        Args:
            data: The response data from the OAuth provider

        Returns:
            M2MTokenResponse containing the access token and metadata

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required_fields = ["access_token", "token_type", "expires_in"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            raise ValueError(f"Missing required fields in response: {missing_fields}")

        return M2MTokenResponse(**data)

    def _request_token(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        audience: str = "",
        timeout: Optional[int] = None,
    ) -> M2MTokenResponse:
        payload, headers = self._prepare_token_request(
            client_id, client_secret, audience
        )

        original_timeout = self.timeout
        if timeout is not None:
            self.timeout = int(timeout)

        try:
            response = self._make_request(
                HTTPMethods.POST,
                "/oauth/token",
                data=payload.model_dump(),
                headers=headers,
            )
            data = response.json()
            return self._process_token_response(data)
        finally:
            self.timeout = original_timeout

    async def get_token(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        audience: str = "",
        timeout: int = 30,
    ) -> M2MTokenResponse:
        """
        Get a machine-to-machine access token from OAuth/OIDC provider.

        Args:
            client_id: The OAuth client ID (uses settings.service_account_client_id if not provided)
            client_secret: The OAuth client secret (uses settings.service_account_client_secret if not provided)
            audience: The API audience (identifier)
            timeout: Request timeout in seconds

        Returns:
            M2MTokenResponse containing the access token and metadata

        Raises:
            TesseraClientError: If the request fails with a client error
            TesseraServerError: If the request fails with a server error
            TesseraError: For other unexpected failures
            ValueError: If the response is invalid or credentials are missing
        """
        return await asyncio.to_thread(
            self._request_token, client_id, client_secret, audience, timeout
        )

    def get_token_sync(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        audience: str = "",
        timeout: int = 30,
    ) -> M2MTokenResponse:
        """
        Synchronous version of get_token for use in non-async contexts.

        Args:
            client_id: The OAuth client ID (uses settings.service_account_client_id if not provided)
            client_secret: The OAuth client secret (uses settings.service_account_client_secret if not provided)
            audience: The API audience (identifier)
            timeout: Request timeout in seconds

        Returns:
            M2MTokenResponse containing the access token and metadata

        Raises:
            TesseraClientError: If the request fails with a client error
            TesseraServerError: If the request fails with a server error
            TesseraError: For other unexpected failures
            ValueError: If the response is invalid or credentials are missing
        """
        return self._request_token(client_id, client_secret, audience, timeout)


# Convenience function for quick token retrieval
async def get_m2m_token(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    audience: str = "",
    provider_domain: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Convenience function to get an M2M access token.

    Args:
        client_id: The OAuth client ID (uses settings.service_account_client_id if not provided)
        client_secret: The OAuth client secret (uses settings.service_account_client_secret if not provided)
        audience: The API audience (identifier)
        provider_domain: OAuth/OIDC provider domain (optional, uses settings if not provided)
        timeout: Request timeout in seconds

    Returns:
        The access token string

    Raises:
        TesseraClientError: If the request fails with a client error
        TesseraServerError: If the request fails with a server error
        TesseraError: For other unexpected failures
        ValueError: If the response is invalid or credentials are missing
    """
    client = M2MTokenClient(provider_domain)
    response = await client.get_token(client_id, client_secret, audience, timeout)
    return response.access_token


def get_m2m_token_sync(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    audience: str = "",
    provider_domain: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Synchronous convenience function to get an M2M access token.

    Args:
        client_id: The OAuth client ID (uses settings.service_account_client_id if not provided)
        client_secret: The OAuth client secret (uses settings.service_account_client_secret if not provided)
        audience: The API audience (identifier)
        provider_domain: OAuth/OIDC provider domain (optional, uses settings if not provided)
        timeout: Request timeout in seconds

    Returns:
        The access token string

    Raises:
        TesseraClientError: If the request fails with a client error
        TesseraServerError: If the request fails with a server error
        TesseraError: For other unexpected failures
        ValueError: If the response is invalid or credentials are missing
    """
    client = M2MTokenClient(provider_domain)
    response = client.get_token_sync(client_id, client_secret, audience, timeout)
    return response.access_token
