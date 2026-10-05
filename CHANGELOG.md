# Changelog

## 0.2.0

- Add shared MCP event, diagnostic, origin-tag, and completion-channel contracts.
- Add bounded parsing for namespaced MCP result metadata with stable error codes.
- Add a stricter MCP event envelope that preserves producer-assigned event IDs
  and timestamps, requires `origin:mcp`, and accepts only object-shaped event data.
- Publish canonical metadata fixtures and a generated language-neutral JSON Schema.

The MCP contracts are additive. Existing SDK APIs and metadata-free MCP tools are
unchanged. Provider conformance automation is deferred to
[issue #117](https://github.com/tesserahq/tessera-sdk-py/issues/117).
