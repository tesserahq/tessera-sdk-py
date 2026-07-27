"""
Main Sendly client for interacting with the Sendly API.
"""

import logging
from typing import Optional
import requests

from .._base.client import BaseClient
from ...constants import HTTPMethods
from .schemas.create_email_request import CreateEmailRequest
from .schemas.create_email_response import CreateEmailResponse
from .schemas.send_broadcast_request import SendBroadcastRequest
from .schemas.send_broadcast_response import SendBroadcastResponse
from .schemas.get_broadcast_response import GetBroadcastResponse
from ...config import get_settings

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
        """
        endpoint = "/emails"

        response = self._make_request(
            HTTPMethods.POST, endpoint, data=request.model_dump(mode="json")
        )
        return CreateEmailResponse(**response.json())

    def send_broadcast(
        self,
        request: SendBroadcastRequest,
    ) -> SendBroadcastResponse:
        """
        Fan a single piece of content out to a list of recipients.

        Returns immediately with accept-time counts; rendering and sending
        happen asynchronously. Use get_broadcast() to poll progress.

        Args:
            request: SendBroadcastRequest object containing the shared
                content options and the recipient list

        Returns:
            SendBroadcastResponse containing the generated batch_id and
            accept-time queued/suppressed counts
        """
        endpoint = "/broadcasts/send"

        response = self._make_request(
            HTTPMethods.POST, endpoint, data=request.model_dump(mode="json")
        )
        return SendBroadcastResponse(**response.json())

    def get_broadcast(
        self,
        batch_id: str,
        project_id: Optional[str] = None,
    ) -> GetBroadcastResponse:
        """
        Get accept-time counts plus live prepare/send progress for one batch.

        Args:
            batch_id: The batch_id returned by send_broadcast()
            project_id: Optional project scope for authorization. batch_id
                is server-generated and globally unique, so this is not
                required to locate the batch — omit it if you hold a
                global/super-admin grant.

        Returns:
            GetBroadcastResponse containing the batch's current counts and
            whether the send stage has finished for every recipient
        """
        endpoint = f"/broadcasts/{batch_id}"
        params = {"project_id": project_id} if project_id else None

        response = self._make_request(HTTPMethods.GET, endpoint, params=params)
        return GetBroadcastResponse(**response.json())
