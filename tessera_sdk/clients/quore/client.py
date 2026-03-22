"""
Main Quore client for interacting with the Quore API.
"""

import logging
from typing import Optional, Dict, Any
import requests

from .._base.client import BaseClient
from ...constants import HTTPMethods
from .schemas.summarize_request import SummarizeRequest
from .schemas.summarize_response import SummarizeResponse

logger = logging.getLogger(__name__)


class QuoreClient(BaseClient):
    """
    A client for interacting with the Quore API.

    This client provides methods for text summarization and other NLP operations.
    """

    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        timeout: int = 60,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the Quore client.

        Args:
            base_url: The base URL of the Quore API (e.g., "https://quore-api.yourdomain.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            session: Optional requests.Session instance to use
        """
        super().__init__(
            base_url=base_url,
            api_token=api_token,
            timeout=timeout,
            session=session,
            service_name="quore",
        )

    def summarize(
        self,
        project_id: str,
        prompt_id: str,
        text: str,
        query: str,
        labels: Optional[Dict[str, Any]] = None,
    ) -> SummarizeResponse:
        """
        Summarize text using the specified prompt.
        """
        request_data = SummarizeRequest(
            prompt_id=prompt_id, text=text, labels=labels or {}, query=query
        )

        endpoint = f"/projects/{project_id}/summarize"

        response = self._make_request(
            HTTPMethods.POST, endpoint, data=request_data.model_dump()
        )
        return SummarizeResponse(**response.json())
