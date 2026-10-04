import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tessera_sdk.infra.events import Event

from .contracts import ToolDebug
from .origin import get_origin

MCP_EVENTS_META_KEY = "com.tesserahq/events"
MCP_DEBUG_META_KEY = "com.tesserahq/debug"


@dataclass(frozen=True)
class MetadataLimits:
    max_events: int = 100
    max_event_bytes: int = 256 * 1024
    max_debug_bytes: int = 1024 * 1024
    max_depth: int = 12
    max_items: int = 10_000


class MCPMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[Event] = Field(default_factory=list)
    debug: ToolDebug | None = None

    @field_validator("events")
    @classmethod
    def validate_event_origins(cls, events: list[Event]) -> list[Event]:
        for event in events:
            if get_origin(event.tags) is None:
                raise ValueError("Every MCP event must contain one origin:* tag")
        return events


def parse_mcp_metadata(
    meta: Mapping[str, Any] | None,
    limits: MetadataLimits | None = None,
) -> MCPMetadata:
    """Parse recognized MCP metadata and enforce transport-safe limits.

    Unknown namespaced metadata is intentionally ignored. Unnamespaced aliases for
    Tessera channels are rejected so providers cannot accidentally publish a
    non-portable contract.
    """
    raw = dict(meta or {})
    if "events" in raw or "debug" in raw:
        raise ValueError("Tessera MCP metadata must use namespaced keys")

    limits = limits or MetadataLimits()
    raw_events = raw.get(MCP_EVENTS_META_KEY, [])
    raw_debug = raw.get(MCP_DEBUG_META_KEY)
    if not isinstance(raw_events, list):
        raise TypeError(f"{MCP_EVENTS_META_KEY} must be a list")
    if len(raw_events) > limits.max_events:
        raise ValueError("MCP event count exceeds the configured limit")

    _assert_payload_limits(raw_events, limits.max_event_bytes, limits)
    if raw_debug is not None:
        _assert_payload_limits(raw_debug, limits.max_debug_bytes, limits)

    return MCPMetadata(events=raw_events, debug=raw_debug)


def _assert_payload_limits(value: Any, max_bytes: int, limits: MetadataLimits) -> None:
    encoded = json.dumps(value, separators=(",", ":"), default=str).encode()
    if len(encoded) > max_bytes:
        raise ValueError("MCP metadata exceeds the configured byte limit")
    depth, items = _measure(value)
    if depth > limits.max_depth:
        raise ValueError("MCP metadata exceeds the configured depth limit")
    if items > limits.max_items:
        raise ValueError("MCP metadata exceeds the configured item limit")


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
