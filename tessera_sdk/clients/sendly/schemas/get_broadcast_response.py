from pydantic import BaseModel


class GetBroadcastResponse(BaseModel):
    """Schema for the response to fetching a broadcast batch's status."""

    batch_id: str
    """Server-generated identifier for this broadcast batch."""

    queued_count: int
    """Number of recipients queued for sending (fixed at accept time)."""

    suppressed_count: int
    """Number of recipients skipped because they had previously unsubscribed."""

    prepared_count: int
    """Number of recipients whose content has been rendered so far."""

    finished: bool
    """True once the send stage has been attempted for every queued recipient.
    Does not track post-send webhook updates (opened/clicked/bounced, etc.)."""
