from pydantic import BaseModel


class SendBroadcastResponse(BaseModel):
    """Schema for the immediate response to sending a broadcast."""

    batch_id: str
    """Server-generated identifier for this broadcast batch."""

    queued_count: int
    """Number of recipients queued for sending (fixed at accept time)."""

    suppressed_count: int
    """Number of recipients skipped because they had previously unsubscribed."""
