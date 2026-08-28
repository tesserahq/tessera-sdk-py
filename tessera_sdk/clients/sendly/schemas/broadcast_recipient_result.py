"""Schemas for GET /broadcasts/{batch_id}/recipients."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class BroadcastRecipientResult(BaseModel):
    """One recipient's results within a broadcast batch.

    Starts from the submitted recipient (not the email list), so a
    suppressed recipient or one whose preparation failed still appears here
    — email_id/email_status/opened_at/clicked_at are null in that case,
    while suppressed/prepared explain the known outcome.
    """

    id: UUID
    """Sendly's internal identifier for this recipient row."""

    client_reference_id: Optional[UUID] = None
    """The caller-supplied reference from the original request, if any."""

    email: str
    """The immutable submitted email address."""

    suppressed: bool
    """True if this recipient was excluded from sending (unsubscribed)."""

    prepared: bool
    """True once the prepare stage has processed this recipient — whether or
    not it produced an email (a suppressed-since-acceptance recipient is
    also `prepared=True` with no email)."""

    email_id: Optional[UUID] = None
    """The resulting email's id, if one was created for this recipient."""

    email_status: Optional[str] = None
    """The resulting email's current delivery status, if one exists."""

    opened_at: Optional[datetime] = None
    """Earliest known open, if any. Independent of email_status."""

    clicked_at: Optional[datetime] = None
    """Earliest known click, if any. Independent of opened_at — a click
    never implies an open."""


class BroadcastRecipientPageResponse(BaseModel):
    """Paginated list of BroadcastRecipientResult.

    Ordered by a stable (created_at, id) tie-breaker server-side, so paging
    through `page`/`size` never skips or duplicates a recipient as long as
    every page up to `pages` is fetched.
    """

    items: List[BroadcastRecipientResult]
    total: int
    page: int
    size: int
    pages: int
