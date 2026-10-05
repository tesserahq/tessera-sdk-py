"""Shared MCP wire contracts for Tessera providers and clients."""

from .contracts import (
    CompletionInclude,
    PublicEventData,
    ResourceReference,
    ToolDebug,
    ToolExecutionRecord,
    ToolExecutionStatus,
    TruncationMarker,
)
from .metadata import (
    MCP_DEBUG_META_KEY,
    MCP_EVENTS_META_KEY,
    MCPEvent,
    MCPMetadata,
    MCPMetadataError,
    MetadataLimits,
    parse_mcp_metadata,
)
from .origin import ORIGIN_TAG_PREFIX, get_origin, set_origin
from .resources import load_contract_fixture

__all__ = [
    "MCP_DEBUG_META_KEY",
    "MCP_EVENTS_META_KEY",
    "ORIGIN_TAG_PREFIX",
    "CompletionInclude",
    "MCPEvent",
    "MCPMetadata",
    "MCPMetadataError",
    "MetadataLimits",
    "PublicEventData",
    "ResourceReference",
    "ToolDebug",
    "ToolExecutionRecord",
    "ToolExecutionStatus",
    "TruncationMarker",
    "get_origin",
    "load_contract_fixture",
    "parse_mcp_metadata",
    "set_origin",
]
