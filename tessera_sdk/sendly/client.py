"""
Main Sendly client for interacting with the Sendly API.
"""

import logging
from typing import Optional
import requests

from ..base.client import BaseClient
from ..constants import HTTPMethods
from .schemas.send_email_request import SendEmailRequest
from .schemas.send_email_response import SendEmailResponse
from .exceptions import (
    SendlyError,
    SendlyClientError,
    SendlyServerError,
    SendlyAuthenticationError,
    SendlyNotFoundError,
    SendlyValidationError,
)

logger = logging.getLogger(__name__)


class SendlyClient(BaseClient):
    """
    A client for interacting with the Sendly API.

    This client provides methods for sending emails.
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
        Initialize the Sendly client.

        Args:
            base_url: The base URL of the Sendly API (e.g., "https://sendly-api.yourdomain.com")
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
            service_name="sendly",
        )

    def _handle_sendly_exceptions(self, e: Exception):
        """Convert base exceptions to Sendly-specific exceptions."""
        from ..base.exceptions import (
            TesseraAuthenticationError,
            TesseraNotFoundError,
            TesseraValidationError,
            TesseraClientError,
            TesseraServerError,
            TesseraError,
        )

        if isinstance(e, TesseraAuthenticationError):
            raise SendlyAuthenticationError(str(e), e.status_code)
        elif isinstance(e, TesseraNotFoundError):
            raise SendlyNotFoundError(str(e), e.status_code)
        elif isinstance(e, TesseraValidationError):
            raise SendlyValidationError(str(e), e.status_code)
        elif isinstance(e, TesseraClientError):
            raise SendlyClientError(str(e), e.status_code)
        elif isinstance(e, TesseraServerError):
            raise SendlyServerError(str(e), e.status_code)
        elif isinstance(e, TesseraError):
            raise SendlyError(str(e), e.status_code)
        else:
            raise e

    def send_email(
        self,
        request: SendEmailRequest,
    ) -> SendEmailResponse:
        """
        Send an email.

        Args:
            request: SendEmailRequest object containing all email details

        Returns:
            SendEmailResponse object containing the email sending result

        Raises:
            SendlyValidationError: If request data is invalid
            SendlyAuthenticationError: If authentication fails
            SendlyServerError: If the server encounters an error

        Example:
            >>> from tessera_sdk.sendly.schemas import SendEmailRequest
            >>> client = SendlyClient(base_url="https://sendly.example.com", api_token="your-token")
            >>> request = SendEmailRequest(
            ...     name="Welcome Email",
            ...     tenant_id="tenant-123",
            ...     provider_id="provider-456",
            ...     from_email="noreply@example.com",
            ...     subject="Welcome!",
            ...     html="<html><body>Hello ${name}!</body></html>",
            ...     to=["user@example.com"],
            ...     template_variables={"name": "John"}
            ... )
            >>> response = client.send_email(request)
            >>> print(response.status)  # 'sent'
        """
        endpoint = "/emails/send"

        try:
            response = self._make_request(
                HTTPMethods.POST, endpoint, data=request.model_dump()
            )
            return SendEmailResponse(**response.json())
        except Exception as e:
            self._handle_sendly_exceptions(e)
            raise  # This should never be reached as _handle_sendly_exceptions always raises
