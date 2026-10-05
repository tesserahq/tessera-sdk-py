import json
from importlib.resources import files
from typing import Any


def load_contract_fixture(name: str) -> dict[str, Any]:
    """Load a canonical provider fixture bundled with the SDK."""
    if not name.endswith(".json") or "/" in name or "\\" in name:
        raise ValueError("Fixture name must be a JSON filename")
    resource = files("tessera_sdk.mcp.fixtures").joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))
