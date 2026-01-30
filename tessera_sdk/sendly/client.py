"""
Main Sendly client for interacting with the Sendly API.
"""

import logging
from typing import Optional
import requests

from ..base.client import BaseClient
from ..constants import HTTPMethods
from .schemas.create_email_request import CreateEmailRequest
from .schemas.create_email_response import CreateEmailResponse
from ..config import get_settings

logger = logging.getLogger(__name__)


class SendlyClient(BaseClient):
    """
    A client for interacting with the Sendly API.

    This client provides methods for sending emails.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the Sendly client.

        Args:
            base_url: The base URL of the Sendly API (e.g., "https://sendly-api.yourdomain.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            session: Optional requests.Session instance to use
        """
        if base_url is None:
            base_url = get_settings().sendly_api_url

        super().__init__(
            base_url=base_url,
            api_token=api_token,
            timeout=timeout,
            session=session,
            service_name="sendly",
        )

    def create_email(
        self,
        request: CreateEmailRequest,
    ) -> CreateEmailResponse:
        """
        Send an email.

        Args:
            request: CreateEmailRequest object containing all email details

        Returns:
            CreateEmailResponse object containing the email sending result

        Raises:
            SendlyValidationError: If request data is invalid
            SendlyAuthenticationError: If authentication fails
            SendlyServerError: If the server encounters an error

        Example:
            >>> from tessera_sdk.sendly.schemas import CreateEmailRequest
            >>> client = SendlyClient(base_url="https://sendly.example.com", api_token="your-token")
            >>> request = CreateEmailRequest(
            ...     name="Welcome Email",
            ...     project_id="a0ca28dc-b064-43b7-90c4-208031508397",
            ...     provider="provider-456",
            ...     from_email="noreply@example.com",
            ...     subject="Welcome!",
            ...     html="<html><body>Hello ${name}!</body></html>",
            ...     to=["user@example.com"],
            ...     template_variables={"name": "John"}
            ... )
            >>> response = client.create_email(request)
            >>> print(response.status)  # 'sent'
        """
        endpoint = "/emails"

        response = self._make_request(
            HTTPMethods.POST, endpoint, data=request.model_dump()
        )
        return CreateEmailResponse(**response.json())
