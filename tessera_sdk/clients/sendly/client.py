"""
Main Sendly client for interacting with the Sendly API.
"""

import logging
from typing import Any, Dict, Iterator, Optional
import requests

from .._base.client import BaseClient
from ...constants import HTTPMethods
from .schemas.create_email_request import CreateEmailRequest
from .schemas.create_email_response import CreateEmailResponse
from .schemas.send_broadcast_request import SendBroadcastRequest
from .schemas.send_broadcast_response import SendBroadcastResponse
from .schemas.get_broadcast_response import GetBroadcastResponse
from .schemas.broadcast_recipient_result import BroadcastRecipientPageResponse
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

    def list_broadcast_recipients(
        self,
        batch_id: str,
        project_id: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> BroadcastRecipientPageResponse:
        """
        Get paginated per-recipient results for one broadcast batch: each
        recipient's submitted identity, suppression/preparation outcome,
        resulting email (when one exists), and first-open/first-click
        timestamps — in one request instead of an N+1 series of email
        lookups.

        Results are ordered by a stable tie-breaker server-side, so fetching
        every page up to `.pages` visits each recipient exactly once. A
        suppressed recipient or a preparation failure is still returned,
        with email_id/email_status/opened_at/clicked_at all null — that
        distinguishes those outcomes from "not yet prepared".

        Args:
            batch_id: The batch_id returned by send_broadcast()
            project_id: Optional project scope for authorization. batch_id
                is server-generated and globally unique, so this is not
                required to locate the batch — omit it if you hold a
                global/super-admin grant.
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            BroadcastRecipientPageResponse with items and pagination
            metadata (total/page/size/pages)
        """
        endpoint = f"/broadcasts/{batch_id}/recipients"
        params = {"page": page, "size": size}
        if project_id:
            params["project_id"] = project_id

        response = self._make_request(HTTPMethods.GET, endpoint, params=params)
        return BroadcastRecipientPageResponse(**response.json())

    def iter_broadcast_recipients(
        self,
        batch_id: str,
        project_id: Optional[str] = None,
        size: int = 50,
    ) -> Iterator[Any]:
        """
        Yield every recipient result for one broadcast batch, transparently
        walking every page.

        `list_broadcast_recipients()` returns a single page only — a batch
        with more recipients than `size` requires the caller to loop over
        `page`/`pages` itself. This does that looping, so a caller (e.g. an
        engagement-polling task) can iterate the full result set without
        reimplementing page traversal or risking silently processing only
        the first page.

        Args:
            batch_id: The batch_id returned by send_broadcast()
            project_id: Optional project scope, forwarded to each page
                request. See list_broadcast_recipients() for details.
            size: Page size to request internally.

        Yields:
            BroadcastRecipientResult, one per recipient, in the same stable
            server-side order as list_broadcast_recipients().
        """
        page = 1
        while True:
            response = self.list_broadcast_recipients(
                batch_id=batch_id,
                project_id=project_id,
                page=page,
                size=size,
            )
            for item in response.items:
                yield item
            if page >= response.pages:
                break
            page += 1

    def list_emails(
        self,
        project_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Dict[str, Any]:
        """
        List emails, optionally filtered by project, broadcast batch, tag,
        or status (paginated).

        For example, to find who opened a given broadcast:
        list_emails(batch_id=batch_id, status="opened").

        Args:
            project_id: Optional project ID to filter emails by.
            batch_id: Optional broadcast batch_id to filter emails by.
            tag: Optional exact tag membership filter.
            status: Optional email status filter (e.g. 'opened', 'delivered').
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            Paginated response dict with items and pagination metadata.
        """
        params = {
            "project_id": project_id,
            "batch_id": batch_id,
            "tag": tag,
            "status": status,
            "page": page,
            "size": size,
        }
        params = {key: value for key, value in params.items() if value is not None}

        response = self._make_request(HTTPMethods.GET, "/emails", params=params)
        return response.json()

    def iter_emails(
        self,
        project_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        size: int = 50,
    ) -> Iterator[Dict[str, Any]]:
        """
        Yield every email matching the given filters, transparently walking
        every page.

        `list_emails()` returns a single page only (default size 50) — a
        filter matching more emails than that silently truncates unless the
        caller loops over `page`/`pages` itself. This does that looping, so
        e.g. a broadcast with hundreds of recipients can be fully consumed
        via `iter_emails(batch_id=batch_id)` without the caller having to
        reimplement page traversal.

        Args:
            project_id: Optional project ID to filter emails by.
            batch_id: Optional broadcast batch_id to filter emails by.
            tag: Optional exact tag membership filter.
            status: Optional email status filter (e.g. 'opened', 'delivered').
            size: Page size to request internally.

        Yields:
            Each email as a dict, in the same order list_emails() returns
            within a page.
        """
        page = 1
        while True:
            response = self.list_emails(
                project_id=project_id,
                batch_id=batch_id,
                tag=tag,
                status=status,
                page=page,
                size=size,
            )
            items = response.get("items", [])
            for item in items:
                yield item
            total_pages = response.get("pages", 1)
            if page >= total_pages:
                break
            page += 1
