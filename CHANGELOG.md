# Changelog

## Unreleased

- Fix the authorization cache reading a different key (`authorized`) than it
  writes (`allowed`): with `AUTHORIZATION_CACHE_ENABLED=true`, every cached
  decision, including allowed ones, was answered with 403.
- Add first-class event and tool-execution include channels to `ModelaClient`
  streaming and non-streaming completions.
- Parse completion extensions using the shared MCP contracts and preserve
  committed events on Modela completion exceptions.
- Keep the legacy nested `extra_body.include` request shape compatible while
  rejecting conflicting include sources.

## 0.2.0

- Add shared MCP event, diagnostic, origin-tag, and completion-channel contracts.
- Add bounded parsing for namespaced MCP result metadata with stable error codes.
- Add a stricter MCP event envelope that preserves producer-assigned event IDs
  and timestamps, requires `origin:mcp`, and accepts only object-shaped event data.
- Publish representative metadata fixtures for the Python parser contract.

The MCP contracts are additive. Existing SDK APIs and metadata-free MCP tools are
unchanged.
