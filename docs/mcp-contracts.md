# MCP event and diagnostic contracts

`tessera_sdk.mcp` is the source of truth for metadata shared by Tessera MCP
providers, Modela, and completion clients. The module has no FastMCP dependency.
Providers can use FastMCP or another implementation while emitting the same wire
contract.

## Metadata keys

- `com.tesserahq/events`: a list of committed Tessera `Event` objects.
- `com.tesserahq/debug`: an intentionally selected `ToolDebug` projection.

Every MCP-originated event has exactly one `origin:*` tag. Use `set_origin`
instead of manipulating that tag directly. Unknown namespaced metadata is ignored;
the unnamespaced aliases `events` and `debug` are rejected.

```python
from tessera_sdk.mcp import parse_mcp_metadata

metadata = parse_mcp_metadata(tool_result_meta)
for event in metadata.events:
    process(event)
```

`parse_mcp_metadata` validates the contract and applies bounded count, byte,
depth, and item limits. Callers decide whether an invalid provider response is
dropped, logged, or raised; the SDK never logs payload values.

## Provider conformance

`check_provider_contract` compares `tools/list` and representative `tools/call`
snapshots before and after metadata adoption. It verifies that existing tools and
output schemas remain stable, normal results are unchanged, and additive metadata
is valid. Canonical JSON fixtures are bundled under `tessera_sdk.mcp.fixtures` and
can be consumed through `load_contract_fixture`. A language-neutral JSON Schema is
bundled under `tessera_sdk.mcp.schemas` and exposed by `load_contract_schema` for
providers implemented outside Python.

The conformance report establishes wire compatibility only. It does not approve
product-specific event data, grant Modela permissions, or make authorization
decisions.
