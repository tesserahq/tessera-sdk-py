"""
Main Vaulta client for interacting with the Vaulta API.
"""

import logging
from typing import Optional
import requests

from ..base.client import BaseClient
from ..constants import HTTPMethods
from .schemas.asset_response import AssetResponse
from .exceptions import (
    VaultaError,
    VaultaClientError,
    VaultaServerError,
    VaultaAuthenticationError,
    VaultaNotFoundError,
    VaultaValidationError,
)

logger = logging.getLogger(__name__)


class VaultaClient(BaseClient):
    """
    A client for interacting with the Vaulta API.

    This client provides methods for managing assets.
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
        Initialize the Vaulta client.

        Args:
            base_url: The base URL of the Vaulta API (e.g., "https://vaulta-api.yourdomain.com")
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
            service_name="vaulta",
        )

    def _handle_vaulta_exceptions(self, e: Exception):
        """Convert base exceptions to Vaulta-specific exceptions."""
        from ..base.exceptions import (
            TesseraAuthenticationError,
            TesseraNotFoundError,
            TesseraValidationError,
            TesseraClientError,
            TesseraServerError,
            TesseraError,
        )

        if isinstance(e, TesseraAuthenticationError):
            raise VaultaAuthenticationError(str(e), e.status_code)
        elif isinstance(e, TesseraNotFoundError):
            raise VaultaNotFoundError(str(e), e.status_code)
        elif isinstance(e, TesseraValidationError):
            raise VaultaValidationError(str(e), e.status_code)
        elif isinstance(e, TesseraClientError):
            raise VaultaClientError(str(e), e.status_code)
        elif isinstance(e, TesseraServerError):
            raise VaultaServerError(str(e), e.status_code)
        elif isinstance(e, TesseraError):
            raise VaultaError(str(e), e.status_code)
        else:
            raise e

    def get_asset(self, asset_id: str) -> AssetResponse:
        """
        Get an asset by its ID.

        Args:
            asset_id: The ID of the asset to retrieve

        Returns:
            AssetResponse object containing the asset data

        Raises:
            VaultaNotFoundError: If asset is not found
            VaultaAuthenticationError: If authentication fails
            VaultaValidationError: If asset_id is invalid
        """
        endpoint = f"/assets/{asset_id}"

        try:
            response = self._make_request(HTTPMethods.GET, endpoint)
            return AssetResponse(**response.json())
        except Exception as e:
            self._handle_vaulta_exceptions(e)
