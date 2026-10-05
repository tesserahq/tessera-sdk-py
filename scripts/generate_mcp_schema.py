"""Regenerate the checked-in language-neutral MCP metadata schema."""

import json
from pathlib import Path

from tessera_sdk.mcp import mcp_metadata_json_schema

SCHEMA_PATH = (
    Path(__file__).parents[1]
    / "tessera_sdk"
    / "mcp"
    / "schemas"
    / "metadata.schema.json"
)


def main() -> None:
    schema = json.dumps(mcp_metadata_json_schema(), indent=2) + "\n"
    SCHEMA_PATH.write_text(schema, encoding="utf-8")


if __name__ == "__main__":
    main()
