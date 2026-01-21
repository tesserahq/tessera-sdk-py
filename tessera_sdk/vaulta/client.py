"""
Main Vaulta client for interacting with the Vaulta API.
"""

import logging
from typing import Optional
import requests

from ..base.client import BaseClient
from ..constants import HTTPMethods
from .schemas.asset_response import AssetResponse

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
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the Vaulta client.

        Args:
            base_url: The base URL of the Vaulta API (e.g., "https://vaulta-api.yourdomain.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            session: Optional requests.Session instance to use
        """
        super().__init__(
            base_url=base_url,
            api_token=api_token,
            timeout=timeout,
            session=session,
            service_name="vaulta",
        )

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

        response = self._make_request(HTTPMethods.GET, endpoint)
        return AssetResponse(**response.json())
