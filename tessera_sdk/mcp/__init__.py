"""Shared MCP wire contracts for Tessera providers and clients."""

from .conformance import ConformanceReport, check_provider_contract
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
    MCPMetadata,
    MetadataLimits,
    parse_mcp_metadata,
)
from .origin import ORIGIN_TAG_PREFIX, get_origin, set_origin
from .resources import (
    contract_json_schemas,
    load_contract_fixture,
    load_contract_schema,
)

__all__ = [
    "MCP_DEBUG_META_KEY",
    "MCP_EVENTS_META_KEY",
    "ORIGIN_TAG_PREFIX",
    "CompletionInclude",
    "ConformanceReport",
    "MCPMetadata",
    "MetadataLimits",
    "PublicEventData",
    "ResourceReference",
    "ToolDebug",
    "ToolExecutionRecord",
    "ToolExecutionStatus",
    "TruncationMarker",
    "check_provider_contract",
    "contract_json_schemas",
    "get_origin",
    "load_contract_fixture",
    "load_contract_schema",
    "parse_mcp_metadata",
    "set_origin",
]
