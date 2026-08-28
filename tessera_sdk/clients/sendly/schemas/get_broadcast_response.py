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

    delivered_count: int
    """Number of recipient emails that have ever reached 'delivered' status."""

    bounced_count: int
    """Number of recipient emails that have ever reached 'bounced' status."""

    complained_count: int
    """Number of recipient emails that have ever reached 'complained' status."""

    opened_count: int
    """Exact count of recipient emails that have ever recorded a first-open
    webhook, independent of the email's current status — unaffected by
    out-of-order or duplicate webhook delivery."""

    clicked_count: int
    """Exact count of recipient emails that have ever recorded a first-click
    webhook. Same first-occurrence semantics as opened_count: a recipient
    with multiple clicked links, or a retried webhook, still counts once."""
