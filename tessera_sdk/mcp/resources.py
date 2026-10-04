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
from .metadata import MCPMetadata


def contract_json_schemas() -> dict[str, dict[str, Any]]:
    """Return JSON schemas for language-neutral contract generation."""
    models = (
        MCPMetadata,
        PublicEventData,
        ResourceReference,
        ToolDebug,
        ToolExecutionRecord,
        TruncationMarker,
    )
    return {model.__name__: model.model_json_schema() for model in models}


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
