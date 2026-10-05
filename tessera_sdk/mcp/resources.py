import json
from importlib.resources import files
from typing import Any

from .contracts import (
    PublicEventData,
    ResourceReference,
    ToolDebug,
    ToolExecutionRecord,
    TruncationMarker,
)
from .metadata import MCP_DEBUG_META_KEY, MCP_EVENTS_META_KEY, MCPEvent, MCPMetadata

MCP_METADATA_SCHEMA_ID = "https://schemas.tessera.dev/mcp/metadata/v1"


def mcp_metadata_json_schema() -> dict[str, Any]:
    """Generate the language-neutral schema for the MCP ``_meta`` wire shape.

    The parsed model uses ergonomic Python field names while the wire uses
    namespaced keys. Unknown extension keys remain valid, but the ambiguous
    unnamespaced Tessera aliases are explicitly rejected to match the parser.
    """
    schema = MCPMetadata.model_json_schema()
    event_schema = schema["$defs"]["MCPEvent"]
    event_schema["properties"]["tags"] = {
        "type": "array",
        "items": {
            "anyOf": [
                {"const": "origin:mcp"},
                {"type": "string", "not": {"pattern": "^origin:"}},
            ]
        },
        "contains": {"const": "origin:mcp"},
        "minContains": 1,
        "maxContains": 1,
    }
    event_schema["required"] = [*event_schema["required"], "tags"]
    properties = schema["properties"]
    events = properties.pop("events")
    debug = properties.pop("debug")
    properties[MCP_EVENTS_META_KEY] = {
        "anyOf": [events, {"type": "null"}],
        "default": None,
    }
    properties[MCP_DEBUG_META_KEY] = debug
    schema.update(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": MCP_METADATA_SCHEMA_ID,
            "title": "Tessera MCP metadata",
            "additionalProperties": True,
            "propertyNames": {"not": {"enum": ["events", "debug"]}},
        }
    )
    return schema


def contract_json_schemas() -> dict[str, dict[str, Any]]:
    """Return JSON schemas for language-neutral contract generation."""
    models = (
        MCPEvent,
        PublicEventData,
        ResourceReference,
        ToolDebug,
        ToolExecutionRecord,
        TruncationMarker,
    )
    schemas = {model.__name__: model.model_json_schema() for model in models}
    schemas["MCPMetadata"] = mcp_metadata_json_schema()
    return schemas


def load_contract_fixture(name: str) -> dict[str, Any]:
    """Load a canonical provider fixture bundled with the SDK."""
    if not name.endswith(".json") or "/" in name or "\\" in name:
        raise ValueError("Fixture name must be a JSON filename")
    resource = files("tessera_sdk.mcp.fixtures").joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_contract_schema() -> dict[str, Any]:
    """Load the bundled language-neutral MCP metadata JSON Schema."""
    resource = files("tessera_sdk.mcp.schemas").joinpath("metadata.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))
