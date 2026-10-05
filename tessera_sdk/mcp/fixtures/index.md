# MCP metadata fixtures

This directory contains example JSON payloads for the Tessera-owned portion of
an MCP tool result's `_meta` object. The fixtures exercise the same wire format
parsed by `tessera_sdk.mcp.parse_mcp_metadata`.

These files do not represent complete MCP tool results. A tool's normal
`content`, `structuredContent`, and `isError` fields remain outside `_meta` and
are not replaced by these payloads.

## Included fixtures

### `valid_metadata.json`

A valid metadata payload containing:

- one Tessera domain event with a producer-assigned ID and occurrence time;
- exactly one `origin:mcp` tag;
- object-shaped, domain-owned `event_data`; and
- an intentionally selected debug projection.

The example demonstrates structure, not a universal event-data vocabulary.
Producing services remain responsible for defining and reviewing their own
domain payloads and for ensuring that private tool-result values are not copied
into metadata.

### `invalid_multiple_origins.json`

An intentionally invalid payload containing more than one `origin:*` tag. It
proves that an MCP event cannot be attributed to multiple initiating paths and
that `origin:mcp` cannot be combined with another origin.

## How the fixtures are used

The SDK's metadata tests load these files through `load_contract_fixture` and
pass them through the public parser. Controlled Python MCP providers import the
SDK models and parser directly rather than maintaining another schema format.

The shared provider-conformance harness is not part of the current release; it
is tracked in
[tessera-sdk issue #117](https://github.com/tesserahq/tessera-sdk-py/issues/117).
Until that work is implemented, these are parser contract fixtures rather than
a complete certification suite for an MCP provider.

## Maintenance rules

- Keep fixtures free of real customer or production data.
- Use distinctive synthetic identifiers and non-sensitive values.
- Keep valid fixtures synchronized with the public parser behavior.
- Give every invalid fixture one clear contract violation and a test that asserts
  its rejection.
- Add a fixture only when a reusable wire example is clearer than constructing
  the value inside a Python test.
- Update this index whenever a fixture is added, removed, or changes meaning.
