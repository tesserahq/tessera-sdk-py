"""Parsing and safety limits for Tessera data in an MCP result's ``_meta``."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from tessera_sdk.infra.events import Event

from .contracts import ToolDebug
from .origin import get_origin

MCP_EVENTS_META_KEY = "com.tesserahq/events"
MCP_DEBUG_META_KEY = "com.tesserahq/debug"


@dataclass(frozen=True)
class MetadataLimits:
    """Resource limits applied before metadata becomes an in-memory contract.

    These bounds protect ingestion latency and memory use. Applications may
    provide stricter values, but providers cannot use them to bypass validation.
    """

    max_events: int = 100
    max_total_event_bytes: int = 256 * 1024
    max_debug_bytes: int = 1024 * 1024
    max_depth: int = 12
    max_items: int = 10_000


class MCPMetadataError(ValueError):
    """Stable ingestion error that never includes rejected metadata values."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class MCPEvent(Event):
    """Tessera event accepted from MCP result metadata.

    Unlike the general-purpose :class:`Event`, an MCP event must preserve the
    producer-assigned identity and occurrence time used by every other delivery
    transport. Its payload must be a JSON object (or null); the producing service
    remains responsible for validating the domain-specific payload and ensuring
    that it contains no data unsafe for completion clients.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    time: datetime
    event_data: dict[str, Any] | None = None


class MCPMetadata(BaseModel):
    """The Tessera-owned channels recognized in an MCP tool result.

    ``events`` contains committed domain outcomes intended for reactive clients.
    ``debug`` is an optional, provider-selected diagnostic projection. Normal MCP
    ``content`` and ``structuredContent`` remain outside this model and continue
    to carry the complete tool response.
    """

    model_config = ConfigDict(extra="forbid")

    events: list[MCPEvent] = Field(default_factory=list, max_length=100)
    debug: ToolDebug | None = None

    @field_validator("events")
    @classmethod
    def validate_event_origins(cls, events: list[MCPEvent]) -> list[MCPEvent]:
        for event in events:
            if get_origin(event.tags) != "mcp":
                raise ValueError("Every MCP event must contain origin:mcp")
        return events


def parse_mcp_metadata(
    meta: Mapping[str, Any] | None,
    limits: MetadataLimits | None = None,
) -> MCPMetadata:
    """Parse recognized MCP metadata and enforce transport-safe limits.

    This is the common ingestion boundary used by consumers and contract tests.
    Unknown namespaced metadata is intentionally ignored so independent
    extensions can coexist. Unnamespaced aliases for Tessera channels are
    rejected so providers cannot accidentally publish a non-portable contract.

    The returned object contains only Tessera-owned channels. This function does
    not alter or replace the normal MCP result and does not make authorization
    decisions about who may see diagnostic data.
    """
    try:
        if meta is not None and not isinstance(meta, Mapping):
            raise MCPMetadataError(
                "invalid_container", "MCP metadata must be an object"
            )

        raw = dict(meta or {})
        if "events" in raw or "debug" in raw:
            raise MCPMetadataError(
                "unnamespaced_key",
                "Tessera MCP metadata must use namespaced keys",
            )

        limits = limits or MetadataLimits()
        raw_events = raw.get(MCP_EVENTS_META_KEY, [])
        if raw_events is None:
            raw_events = []
        raw_debug = raw.get(MCP_DEBUG_META_KEY)
        if not isinstance(raw_events, list):
            raise MCPMetadataError(
                "invalid_events_type",
                f"{MCP_EVENTS_META_KEY} must be a list or null",
            )
        if len(raw_events) > limits.max_events:
            raise MCPMetadataError(
                "event_count_exceeded",
                "MCP event count exceeds the configured limit",
            )

        _assert_payload_limits(
            raw_events,
            limits.max_total_event_bytes,
            limits,
            channel="events",
        )
        if raw_debug is not None:
            _assert_payload_limits(
                raw_debug,
                limits.max_debug_bytes,
                limits,
                channel="debug",
            )

        return MCPMetadata(events=raw_events, debug=raw_debug)
    except MCPMetadataError:
        raise
    except (TypeError, ValueError, ValidationError):
        raise MCPMetadataError(
            "invalid_contract",
            "MCP metadata does not match the Tessera contract",
        ) from None


def _assert_payload_limits(
    value: Any,
    max_bytes: int,
    limits: MetadataLimits,
    *,
    channel: str,
) -> None:
    encoded = json.dumps(value, separators=(",", ":")).encode()
    if len(encoded) > max_bytes:
        raise MCPMetadataError(
            f"{channel}_bytes_exceeded",
            f"MCP {channel} metadata exceeds the configured byte limit",
        )
    depth, items = _measure(value)
    if depth > limits.max_depth:
        raise MCPMetadataError(
            f"{channel}_depth_exceeded",
            f"MCP {channel} metadata exceeds the configured depth limit",
        )
    if items > limits.max_items:
        raise MCPMetadataError(
            f"{channel}_items_exceeded",
            f"MCP {channel} metadata exceeds the configured item limit",
        )


def _measure(value: Any, depth: int = 0) -> tuple[int, int]:
    if isinstance(value, Mapping):
        measurements = [_measure(item, depth + 1) for item in value.values()]
        return _merge_measurements(depth, len(value), measurements)
    if isinstance(value, (list, tuple)):
        measurements = [_measure(item, depth + 1) for item in value]
        return _merge_measurements(depth, len(value), measurements)
    return depth, 1


def _merge_measurements(
    depth: int, own_items: int, measurements: list[tuple[int, int]]
) -> tuple[int, int]:
    if not measurements:
        return depth, own_items
    return max(item[0] for item in measurements), own_items + sum(
        item[1] for item in measurements
    )
