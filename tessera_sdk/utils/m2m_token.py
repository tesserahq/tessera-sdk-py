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
from ..utils.cache import Cache
import json


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

    cache_key_PREFIX = "m2m_token"

    def __init__(
        self,
        provider_domain: Optional[str] = None,
        timeout: int = 30,
        cache_buffer_seconds: int = 60,
        cache_service: Optional[Cache] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the M2M token client.

        Args:
            provider_domain: OAuth/OIDC provider domain (e.g., 'dev-si3yygt34d0fk7hc.us.auth0.com')
                           If not provided, will use settings.
            timeout: Request timeout in seconds
            cache_buffer_seconds: Number of seconds before token expiry to refresh the token (default: 60)
            session: Optional requests.Session instance to use
        """
        self.settings = get_settings()
        self.provider_domain = provider_domain or self.settings.oidc_domain
        self.cache_buffer_seconds = cache_buffer_seconds
        self.cache_service = cache_service or Cache("m2m_token")

        if not self.provider_domain:
            raise ValueError(
                "Provider domain must be provided either as a parameter or via settings"
            )

        super().__init__(
            base_url=f"https://{self.provider_domain}",
            api_token=None,
            timeout=timeout,
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
        force_refresh: bool = False,
    ) -> M2MTokenResponse:
        """
        Get a machine-to-machine access token from OAuth/OIDC provider.

        Uses cached token from Redis if available and not expired. Set force_refresh=True to ignore cache.

        Args:
            client_id: The OAuth client ID (uses settings.service_account_client_id if not provided)
            client_secret: The OAuth client secret (uses settings.service_account_client_secret if not provided)
            audience: The API audience (identifier)
            timeout: Request timeout in seconds
            force_refresh: If True, ignores cache and fetches a new token

        Returns:
            M2MTokenResponse containing the access token and metadata

        Raises:
            TesseraClientError: If the request fails with a client error
            TesseraServerError: If the request fails with a server error
            TesseraError: For other unexpected failures
            ValueError: If the response is invalid or credentials are missing
        """
        # Use settings defaults if not provided
        resolved_client_id = client_id or self.settings.service_account_client_id
        resolved_audience = audience or self.settings.oidc_api_audience

        # Generate Redis key
        cache_key = self._generate_cache_key(resolved_client_id, resolved_audience)

        # Return cached token if valid and not forcing refresh
        if not force_refresh:
            cached_token = self._get_cached_token(cache_key)
            if cached_token:
                return cached_token

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

    def _get_cached_token(self, cache_key: str) -> Optional[M2MTokenResponse]:
        """
        Retrieve cached token from Redis.

        Args:
            cache_key: The Redis key to retrieve

        Returns:
            M2MTokenResponse if found and valid, None otherwise
        """
        try:
            cached_data = self.cache_service.read(cache_key)
            if cached_data:
                token_data = json.loads(cached_data)
                return M2MTokenResponse(**token_data)
        except Exception as e:
            # Log error but don't fail - just return None to fetch a new token
            logger.warning(f"Failed to retrieve cached token from Redis: {e}")
        return None

    def _cache_token(self, token_response: M2MTokenResponse, cache_key: str) -> None:
        """
        Cache the token response in Redis with expiration.

        Args:
            token_response: The token response to cache
            cache_key: The Redis key for this token
        """
        try:
            # Calculate TTL with buffer (expires_in - buffer_seconds)
            ttl = max(token_response.expires_in - self.cache_buffer_seconds, 1)

            # Store token data as JSON in Redis
            token_json = token_response.model_dump_json()
            self.cache_service.write(cache_key, token_json, ttl=ttl)
        except Exception as e:
            # Log error but don't fail - caching is optional
            logger.warning(f"Failed to cache token in Redis: {e}")

    def clear_cache(
        self, client_id: Optional[str] = None, audience: Optional[str] = None
    ) -> bool:
        """
        Clear cached token(s) from Redis.

        Args:
            client_id: Optional client_id to clear specific token. If not provided, uses settings.
            audience: Optional audience to clear specific token. If not provided, uses settings.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            resolved_client_id = client_id or self.settings.service_account_client_id
            resolved_audience = audience or self.settings.oidc_api_audience
            cache_key = self._generate_cache_key(resolved_client_id, resolved_audience)
            return self.cache_service.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to clear cached token from Redis: {e}")
            return False

    def _generate_cache_key(self, client_id: str, audience: str) -> str:
        """
        Generate a Redis key based on client_id and audience.

        Args:
            client_id: The OAuth client ID
            audience: The API audience

        Returns:
            A Redis key string
        """
        return f"{self.cache_key_PREFIX}:{client_id}:{audience}"


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
