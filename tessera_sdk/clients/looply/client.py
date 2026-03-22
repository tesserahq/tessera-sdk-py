"""
Main Looply client for interacting with the Looply API.
"""

import logging
from typing import Any, Optional
import requests

from .._base.client import BaseClient
from ...constants import HTTPMethods
from ...config import get_settings
from .schemas.contact import Contact, ContactCreateRequest, ContactUpdate
from .schemas.contact_list import (
    ContactList,
    ContactListCreateRequest,
    ContactListUpdate,
    AddMembersRequest,
    ListMembersResponse,
    MemberCountResponse,
    SubscribeResponse,
    ContactListSubscription,
)
from .schemas.contact_interaction import (
    ContactInteraction,
    ContactInteractionCreateRequest,
    ContactInteractionUpdate,
)
from .schemas.waiting_list import (
    WaitingList,
    WaitingListCreateRequest,
    WaitingListUpdate,
    AddWaitingListMembersRequest,
    WaitingListMemberCountResponse,
)

logger = logging.getLogger(__name__)


class LooplyClient(BaseClient):
    """
    A client for interacting with the Looply API.

    Provides methods for managing contacts, contact lists, contact interactions,
    and waiting lists.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the Looply client.

        Args:
            base_url: The base URL of the Looply API (e.g., "https://looply-api.yourdomain.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            session: Optional requests.Session instance to use
        """
        super().__init__(
            base_url=base_url or get_settings().looply_api_url,
            api_token=api_token,
            timeout=timeout,
            session=session,
            service_name="looply",
        )

    # -------------------------------------------------------------------------
    # Contacts
    # -------------------------------------------------------------------------

    def create_contact(self, request: ContactCreateRequest) -> Contact:
        """
        Create a new contact.

        Args:
            request: ContactCreateRequest with contact details.

        Returns:
            The created Contact.
        """
        response = self._make_request(
            HTTPMethods.POST,
            "/contacts",
            data=request.model_dump(mode="json", exclude_none=True),
        )
        return Contact(**response.json())

    def batch_create_contacts(
        self, requests_list: list[ContactCreateRequest]
    ) -> list[Contact]:
        """
        Batch create multiple contacts.

        Args:
            requests_list: List of ContactCreateRequest objects.

        Returns:
            List of created Contact objects.
        """
        response = self._make_request(
            HTTPMethods.POST,
            "/contacts/batch",
            data=[r.model_dump(mode="json", exclude_none=True) for r in requests_list],
        )
        return [Contact(**item) for item in response.json()]

    def list_contacts(self, page: int = 1, size: int = 50) -> dict[str, Any]:
        """
        List all contacts (paginated).

        Args:
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            Paginated response dict with items and pagination metadata.
        """
        response = self._make_request(
            HTTPMethods.GET,
            "/contacts",
            params={"page": page, "size": size},
        )
        return response.json()

    def search_contacts(self, q: str, page: int = 1, size: int = 50) -> dict[str, Any]:
        """
        Search contacts by text.

        Args:
            q: Search query string.
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            Paginated response dict with matching contacts.
        """
        response = self._make_request(
            HTTPMethods.GET,
            "/contacts/search",
            params={"q": q, "page": page, "size": size},
        )
        return response.json()

    def get_contact(self, contact_id: str) -> Contact:
        """
        Get a contact by ID.

        Args:
            contact_id: UUID of the contact.

        Returns:
            Contact object.

        Raises:
            LooplyNotFoundError: If contact is not found.
        """
        response = self._make_request(HTTPMethods.GET, f"/contacts/{contact_id}")
        return Contact(**response.json())

    def update_contact(self, contact_id: str, request: ContactUpdate) -> Contact:
        """
        Update a contact.

        Args:
            contact_id: UUID of the contact.
            request: ContactUpdate with fields to update.

        Returns:
            Updated Contact object.

        Raises:
            LooplyNotFoundError: If contact is not found.
        """
        response = self._make_request(
            HTTPMethods.PUT,
            f"/contacts/{contact_id}",
            data=request.model_dump(mode="json", exclude_none=True),
        )
        return Contact(**response.json())

    def delete_contact(self, contact_id: str) -> None:
        """
        Delete a contact.

        Args:
            contact_id: UUID of the contact.
        """
        self._make_request(HTTPMethods.DELETE, f"/contacts/{contact_id}")

    # -------------------------------------------------------------------------
    # Contact Lists
    # -------------------------------------------------------------------------

    def create_contact_list(self, request: ContactListCreateRequest) -> ContactList:
        """
        Create a new contact list.

        Args:
            request: ContactListCreateRequest with list details.

        Returns:
            The created ContactList.
        """
        response = self._make_request(
            HTTPMethods.POST,
            "/contact-lists",
            data=request.model_dump(mode="json", exclude_none=True),
        )
        return ContactList(**response.json())

    def list_contact_lists(self, page: int = 1, size: int = 50) -> dict[str, Any]:
        """
        List all contact lists (paginated).

        Args:
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            Paginated response dict.
        """
        response = self._make_request(
            HTTPMethods.GET,
            "/contact-lists",
            params={"page": page, "size": size},
        )
        return response.json()

    def list_public_contact_lists(
        self, page: int = 1, size: int = 50
    ) -> dict[str, Any]:
        """
        List public contact lists (paginated).

        Args:
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            Paginated response dict.
        """
        response = self._make_request(
            HTTPMethods.GET,
            "/contact-lists/public",
            params={"page": page, "size": size},
        )
        return response.json()

    def get_contact_list_subscriptions(
        self, page: int = 1, size: int = 50
    ) -> dict[str, Any]:
        """
        Get the current user's subscribed contact lists (paginated).

        Returns:
            Paginated response dict.
        """
        response = self._make_request(
            HTTPMethods.GET,
            "/contact-lists/subscriptions",
            params={"page": page, "size": size},
        )
        return response.json()

    def get_contact_list(self, contact_list_id: str) -> ContactList:
        """
        Get a contact list by ID.

        Args:
            contact_list_id: UUID of the contact list.

        Returns:
            ContactList object.

        Raises:
            LooplyNotFoundError: If contact list is not found.
        """
        response = self._make_request(
            HTTPMethods.GET, f"/contact-lists/{contact_list_id}"
        )
        return ContactList(**response.json())

    def update_contact_list(
        self, contact_list_id: str, request: ContactListUpdate
    ) -> ContactList:
        """
        Update a contact list.

        Args:
            contact_list_id: UUID of the contact list.
            request: ContactListUpdate with fields to update.

        Returns:
            Updated ContactList object.
        """
        response = self._make_request(
            HTTPMethods.PUT,
            f"/contact-lists/{contact_list_id}",
            data=request.model_dump(mode="json", exclude_none=True),
        )
        return ContactList(**response.json())

    def delete_contact_list(self, contact_list_id: str) -> None:
        """
        Delete a contact list.

        Args:
            contact_list_id: UUID of the contact list.
        """
        self._make_request(HTTPMethods.DELETE, f"/contact-lists/{contact_list_id}")

    def add_members_to_contact_list(
        self, contact_list_id: str, request: AddMembersRequest
    ) -> dict[str, Any]:
        """
        Add members to a contact list.

        Args:
            contact_list_id: UUID of the contact list.
            request: AddMembersRequest with contact_ids to add.

        Returns:
            Response dict with added_count.
        """
        response = self._make_request(
            HTTPMethods.POST,
            f"/contact-lists/{contact_list_id}/members",
            data=request.model_dump(mode="json"),
        )
        return response.json()

    def remove_member_from_contact_list(
        self, contact_list_id: str, contact_id: str
    ) -> None:
        """
        Remove a member from a contact list.

        Args:
            contact_list_id: UUID of the contact list.
            contact_id: UUID of the contact to remove.
        """
        self._make_request(
            HTTPMethods.DELETE,
            f"/contact-lists/{contact_list_id}/members/{contact_id}",
        )

    def get_contact_list_members(self, contact_list_id: str) -> dict[str, Any]:
        """
        Get members of a contact list.

        Args:
            contact_list_id: UUID of the contact list.

        Returns:
            Response dict with members.
        """
        response = self._make_request(
            HTTPMethods.GET, f"/contact-lists/{contact_list_id}/members"
        )
        return response.json()

    def get_contact_list_member_count(self, contact_list_id: str) -> dict[str, Any]:
        """
        Get the member count of a contact list.

        Args:
            contact_list_id: UUID of the contact list.

        Returns:
            Response dict with count.
        """
        response = self._make_request(
            HTTPMethods.GET, f"/contact-lists/{contact_list_id}/members/count"
        )
        return response.json()

    def clear_contact_list_members(self, contact_list_id: str) -> None:
        """
        Remove all members from a contact list.

        Args:
            contact_list_id: UUID of the contact list.
        """
        self._make_request(
            HTTPMethods.DELETE, f"/contact-lists/{contact_list_id}/members"
        )

    def get_lists_for_contact(self, contact_id: str) -> list[ContactList]:
        """
        Get all contact lists a contact belongs to.

        Args:
            contact_id: UUID of the contact.

        Returns:
            List of ContactList objects.
        """
        response = self._make_request(
            HTTPMethods.GET,
            f"/contact-lists/contacts/{contact_id}/contact-lists",
        )
        return [ContactList(**item) for item in response.json()]

    def is_contact_list_member(
        self, contact_list_id: str, contact_id: str
    ) -> dict[str, Any]:
        """
        Check if a contact is a member of a contact list.

        Args:
            contact_list_id: UUID of the contact list.
            contact_id: UUID of the contact.

        Returns:
            Dict with contact_list_id, contact_id, and is_member boolean.
        """
        response = self._make_request(
            HTTPMethods.GET,
            f"/contact-lists/{contact_list_id}/members/{contact_id}/is-member",
        )
        return response.json()

    def subscribe_to_contact_list(self, contact_list_id: str) -> dict[str, Any]:
        """
        Subscribe the current user to a public contact list.

        Args:
            contact_list_id: UUID of the contact list.

        Returns:
            Subscribe response dict.
        """
        response = self._make_request(
            HTTPMethods.POST, f"/contact-lists/{contact_list_id}/subscribe"
        )
        return response.json()

    def unsubscribe_from_contact_list(self, contact_list_id: str) -> None:
        """
        Unsubscribe the current user from a public contact list.

        Args:
            contact_list_id: UUID of the contact list.
        """
        self._make_request(
            HTTPMethods.DELETE, f"/contact-lists/{contact_list_id}/unsubscribe"
        )

    # -------------------------------------------------------------------------
    # Contact Interactions
    # -------------------------------------------------------------------------

    def create_contact_interaction(
        self, contact_id: str, request: ContactInteractionCreateRequest
    ) -> ContactInteraction:
        """
        Create an interaction for a contact.

        Args:
            contact_id: UUID of the contact.
            request: ContactInteractionCreateRequest with interaction details.

        Returns:
            The created ContactInteraction.
        """
        response = self._make_request(
            HTTPMethods.POST,
            f"/contacts/{contact_id}/interactions",
            data=request.model_dump(mode="json", exclude_none=True),
        )
        return ContactInteraction(**response.json())

    def list_contact_interactions(
        self, contact_id: str, page: int = 1, size: int = 50
    ) -> dict[str, Any]:
        """
        List interactions for a contact (paginated).

        Args:
            contact_id: UUID of the contact.
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            Paginated response dict.
        """
        response = self._make_request(
            HTTPMethods.GET,
            f"/contacts/{contact_id}/interactions",
            params={"page": page, "size": size},
        )
        return response.json()

    def get_last_contact_interaction(
        self, contact_id: str
    ) -> Optional[ContactInteraction]:
        """
        Get the last interaction for a contact.

        Args:
            contact_id: UUID of the contact.

        Returns:
            ContactInteraction or None if no interactions exist.
        """
        response = self._make_request(
            HTTPMethods.GET, f"/contacts/{contact_id}/interactions/last"
        )
        data = response.json()
        return ContactInteraction(**data) if data else None

    def list_all_interactions(self, page: int = 1, size: int = 50) -> dict[str, Any]:
        """
        List all contact interactions (paginated).

        Args:
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            Paginated response dict.
        """
        response = self._make_request(
            HTTPMethods.GET,
            "/contact-interactions",
            params={"page": page, "size": size},
        )
        return response.json()

    def list_pending_actions(self, page: int = 1, size: int = 50) -> dict[str, Any]:
        """
        Get pending interaction actions (paginated).

        Args:
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            Paginated response dict.
        """
        response = self._make_request(
            HTTPMethods.GET,
            "/contact-interactions/pending-actions",
            params={"page": page, "size": size},
        )
        return response.json()

    def get_interaction(self, interaction_id: str) -> ContactInteraction:
        """
        Get a contact interaction by ID.

        Args:
            interaction_id: UUID of the interaction.

        Returns:
            ContactInteraction object.

        Raises:
            LooplyNotFoundError: If interaction is not found.
        """
        response = self._make_request(
            HTTPMethods.GET, f"/contact-interactions/{interaction_id}"
        )
        return ContactInteraction(**response.json())

    def update_interaction(
        self, interaction_id: str, request: ContactInteractionUpdate
    ) -> ContactInteraction:
        """
        Update a contact interaction.

        Args:
            interaction_id: UUID of the interaction.
            request: ContactInteractionUpdate with fields to update.

        Returns:
            Updated ContactInteraction object.
        """
        response = self._make_request(
            HTTPMethods.PUT,
            f"/contact-interactions/{interaction_id}",
            data=request.model_dump(mode="json", exclude_none=True),
        )
        return ContactInteraction(**response.json())

    def delete_interaction(self, interaction_id: str) -> None:
        """
        Delete a contact interaction.

        Args:
            interaction_id: UUID of the interaction.
        """
        self._make_request(
            HTTPMethods.DELETE, f"/contact-interactions/{interaction_id}"
        )

    # -------------------------------------------------------------------------
    # Waiting Lists
    # -------------------------------------------------------------------------

    def create_waiting_list(self, request: WaitingListCreateRequest) -> WaitingList:
        """
        Create a new waiting list.

        Args:
            request: WaitingListCreateRequest with list details.

        Returns:
            The created WaitingList.
        """
        response = self._make_request(
            HTTPMethods.POST,
            "/waiting-lists",
            data=request.model_dump(mode="json", exclude_none=True),
        )
        return WaitingList(**response.json())

    def list_waiting_lists(self, page: int = 1, size: int = 50) -> dict[str, Any]:
        """
        List all waiting lists (paginated).

        Args:
            page: Page number (1-based).
            size: Number of items per page.

        Returns:
            Paginated response dict.
        """
        response = self._make_request(
            HTTPMethods.GET,
            "/waiting-lists",
            params={"page": page, "size": size},
        )
        return response.json()

    def get_waiting_list(self, waiting_list_id: str) -> WaitingList:
        """
        Get a waiting list by ID.

        Args:
            waiting_list_id: UUID of the waiting list.

        Returns:
            WaitingList object.

        Raises:
            LooplyNotFoundError: If waiting list is not found.
        """
        response = self._make_request(
            HTTPMethods.GET, f"/waiting-lists/{waiting_list_id}"
        )
        return WaitingList(**response.json())

    def update_waiting_list(
        self, waiting_list_id: str, request: WaitingListUpdate
    ) -> WaitingList:
        """
        Update a waiting list.

        Args:
            waiting_list_id: UUID of the waiting list.
            request: WaitingListUpdate with fields to update.

        Returns:
            Updated WaitingList object.
        """
        response = self._make_request(
            HTTPMethods.PUT,
            f"/waiting-lists/{waiting_list_id}",
            data=request.model_dump(mode="json", exclude_none=True),
        )
        return WaitingList(**response.json())

    def delete_waiting_list(self, waiting_list_id: str) -> None:
        """
        Delete a waiting list.

        Args:
            waiting_list_id: UUID of the waiting list.
        """
        self._make_request(HTTPMethods.DELETE, f"/waiting-lists/{waiting_list_id}")

    def add_members_to_waiting_list(
        self, waiting_list_id: str, request: AddWaitingListMembersRequest
    ) -> dict[str, Any]:
        """
        Add members to a waiting list.

        Args:
            waiting_list_id: UUID of the waiting list.
            request: AddWaitingListMembersRequest with contact_ids and optional status.

        Returns:
            Response dict with added_count.
        """
        response = self._make_request(
            HTTPMethods.POST,
            f"/waiting-lists/{waiting_list_id}/members",
            data=request.model_dump(mode="json", exclude_none=True),
        )
        return response.json()

    def remove_member_from_waiting_list(
        self, waiting_list_id: str, contact_id: str
    ) -> None:
        """
        Remove a member from a waiting list.

        Args:
            waiting_list_id: UUID of the waiting list.
            contact_id: UUID of the contact to remove.
        """
        self._make_request(
            HTTPMethods.DELETE,
            f"/waiting-lists/{waiting_list_id}/members/{contact_id}",
        )

    def get_waiting_list_members(self, waiting_list_id: str) -> dict[str, Any]:
        """
        Get members of a waiting list.

        Args:
            waiting_list_id: UUID of the waiting list.

        Returns:
            Response dict with members.
        """
        response = self._make_request(
            HTTPMethods.GET, f"/waiting-lists/{waiting_list_id}/members"
        )
        return response.json()

    def get_waiting_list_member_count(self, waiting_list_id: str) -> dict[str, Any]:
        """
        Get the total member count of a waiting list.

        Args:
            waiting_list_id: UUID of the waiting list.

        Returns:
            Response dict with count.
        """
        response = self._make_request(
            HTTPMethods.GET, f"/waiting-lists/{waiting_list_id}/members/count"
        )
        return response.json()

    def update_waiting_list_member_status(
        self, waiting_list_id: str, contact_id: str, status: str
    ) -> dict[str, Any]:
        """
        Update the status of a waiting list member.

        Args:
            waiting_list_id: UUID of the waiting list.
            contact_id: UUID of the contact.
            status: New status (e.g. "approved", "rejected", "notified").

        Returns:
            Status update response dict.
        """
        response = self._make_request(
            HTTPMethods.PUT,
            f"/waiting-lists/{waiting_list_id}/members/{contact_id}/status",
            params={"status": status},
        )
        return response.json()

    def get_waiting_list_members_by_status(
        self, waiting_list_id: str, status: str
    ) -> dict[str, Any]:
        """
        Get waiting list members filtered by status.

        Args:
            waiting_list_id: UUID of the waiting list.
            status: Status to filter by.

        Returns:
            Response dict with filtered members.
        """
        response = self._make_request(
            HTTPMethods.GET,
            f"/waiting-lists/{waiting_list_id}/members/by-status/{status}",
        )
        return response.json()

    def get_waiting_list_count_by_status(
        self, waiting_list_id: str, status: str
    ) -> dict[str, Any]:
        """
        Get waiting list member count for a specific status.

        Args:
            waiting_list_id: UUID of the waiting list.
            status: Status to count.

        Returns:
            Count response dict.
        """
        response = self._make_request(
            HTTPMethods.GET,
            f"/waiting-lists/{waiting_list_id}/members/by-status/{status}/count",
        )
        return response.json()

    def bulk_update_waiting_list_member_statuses(
        self,
        waiting_list_id: str,
        contact_ids: list[str],
        status: str,
    ) -> dict[str, Any]:
        """
        Bulk update statuses for multiple waiting list members.

        Args:
            waiting_list_id: UUID of the waiting list.
            contact_ids: List of contact UUIDs to update.
            status: New status for all specified members.

        Returns:
            Bulk update response dict.
        """
        response = self._make_request(
            HTTPMethods.POST,
            f"/waiting-lists/{waiting_list_id}/members/bulk-status",
            data={"contact_ids": contact_ids, "status": status},
        )
        return response.json()

    def clear_waiting_list_members(self, waiting_list_id: str) -> None:
        """
        Remove all members from a waiting list.

        Args:
            waiting_list_id: UUID of the waiting list.
        """
        self._make_request(
            HTTPMethods.DELETE, f"/waiting-lists/{waiting_list_id}/members"
        )

    def get_waiting_lists_for_contact(self, contact_id: str) -> list[WaitingList]:
        """
        Get all waiting lists a contact belongs to.

        Args:
            contact_id: UUID of the contact.

        Returns:
            List of WaitingList objects.
        """
        response = self._make_request(
            HTTPMethods.GET,
            f"/waiting-lists/contacts/{contact_id}/waiting-lists",
        )
        return [WaitingList(**item) for item in response.json()]

    def is_waiting_list_member(
        self, waiting_list_id: str, contact_id: str
    ) -> dict[str, Any]:
        """
        Check if a contact is a member of a waiting list.

        Args:
            waiting_list_id: UUID of the waiting list.
            contact_id: UUID of the contact.

        Returns:
            Membership check response dict.
        """
        response = self._make_request(
            HTTPMethods.GET,
            f"/waiting-lists/{waiting_list_id}/members/{contact_id}/is-member",
        )
        return response.json()

    def get_waiting_list_member_status(
        self, waiting_list_id: str, contact_id: str
    ) -> dict[str, Any]:
        """
        Get the status of a contact in a waiting list.

        Args:
            waiting_list_id: UUID of the waiting list.
            contact_id: UUID of the contact.

        Returns:
            Member status response dict with timestamps.
        """
        response = self._make_request(
            HTTPMethods.GET,
            f"/waiting-lists/{waiting_list_id}/members/{contact_id}/status",
        )
        return response.json()
