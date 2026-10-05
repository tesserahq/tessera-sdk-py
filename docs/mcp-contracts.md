# MCP event and diagnostic contracts

`tessera_sdk.mcp` is the source of truth for metadata shared by Tessera MCP
providers, Modela, and completion clients. The module has no FastMCP dependency.
Providers can use FastMCP or another implementation while emitting the same wire
contract.

## Why this module exists

An MCP tool has three audiences with different needs:

1. The model needs the normal, complete tool result so it can continue reasoning.
2. A web or mobile client needs a small, predictable signal that a committed
   domain change occurred so it can refresh the affected UI.
3. An authorized operator may need bounded diagnostics explaining which tools ran.

The normal MCP result remains the source of information for the model and for
customers calling an MCP directly. Tessera metadata is additive; adopting it must
not remove person fields, change a tool's output schema, or otherwise reduce the
existing MCP capability.

The SDK centralizes this wire contract so every Tessera service and future plugin
uses the same vocabulary. Service repositories own their domain behavior, Modela
owns completion orchestration, and this package owns only the shared types,
parsing rules, limits, schemas, fixtures, and contract-validation primitives.

## Mental model and ownership

| Concept | Producer | Consumer | Meaning |
| --- | --- | --- | --- |
| Normal MCP result | Tool provider | Model or direct MCP caller | Complete result of invoking the tool |
| Domain event | Tool provider | Modela, then application clients | A committed business outcome such as `person.created` |
| Tool execution record | Modela | Authorized completion clients | Orchestration telemetry: which tool ran, its status, order, and duration |
| Debug projection | Tool provider | Authorized operators through Modela | Deliberately selected arguments/results for diagnosis |

Domain events and tool execution records are deliberately separate. A tool can
execute successfully without changing domain state, and one tool invocation can
produce more than one committed event. Conversely, execution records describe
the model/tool orchestration and must not be treated as proof that a business
transaction committed.

## End-to-end flow

1. A model asks Modela to call an MCP tool.
2. The provider performs its normal authorization and domain operation.
3. The provider returns its unchanged normal MCP result. If a mutation committed,
   it also places the corresponding Tessera `Event` in `com.tesserahq/events`.
   It may add a deliberately sanitized debug projection in
   `com.tesserahq/debug`.
4. Modela validates recognized metadata using `parse_mcp_metadata`; metadata it
   does not understand is not promoted into completion response channels.
5. Modela independently records the tool execution outcome.
6. A completion caller opts into events and/or tool executions. Debug fields are
   returned only when that caller passes the existing RBAC check.
7. A client reacts to the event—for example, a people listing refreshes after a
   `person.created` event—rather than trying to infer domain changes from tool
   names or arbitrary result bodies.

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

Every invalid input raises `MCPMetadataError`, whose stable `code` can be logged
without including rejected values. The default 256 KiB event-byte limit applies
to the complete events channel, not independently to every event.

Metadata is optional. Read-only tools and plugins that do not produce domain
events continue to return ordinary MCP responses. A provider emits a completed
domain event only after the underlying mutation has committed; accepting or
queuing work is not equivalent to completing that work.

## Contract types

- `MCPMetadata` is the parsed view of the two Tessera-owned metadata channels.
- `MCPEvent` is the stricter event envelope accepted from MCP metadata. It
  requires the producer-assigned ID and occurrence time, an `origin:mcp` tag,
  and object-shaped (or null) `event_data`.
- `PublicEventData` is an optional reusable payload primitive for domains whose
  public contract is exactly an affected resource, related resource identities,
  and changed field names. It is not imposed on every domain event.
- `ToolDebug` is a provider-authored diagnostic projection. It must never be
  populated by blindly copying arbitrary arguments or results.
- `ToolExecutionRecord` is Modela-owned execution telemetry and is not emitted by
  an MCP provider as a domain event.
- `TruncationMarker` tells a completion client that a bounded response channel
  omitted records. It is an explicit partial-response signal, not an event.
- `MetadataLimits` bounds ingestion work so metadata cannot add unbounded latency
  or memory use to a completion.

`CompletionInclude` contains the opt-in response channel names. It does not grant
access: Modela still applies authorization before including diagnostic data.

`parse_mcp_metadata` validates the event envelope, MCP origin, transport limits,
and the structural shape of `event_data`; it cannot determine whether a value in
a domain-owned object is sensitive. Each producing service owns and reviews its
domain event-data model and must test that private values from the complete tool
result never enter metadata. Modela authorization is an additional disclosure
control, not a replacement for producer-side data minimization.

## Provider compatibility

Providers adopting this contract must keep their normal MCP results and advertised
output schemas unchanged. Provider repositories should protect that behavior with
integration tests against their real tools; the shared SDK conformance harness is
deferred to [tessera-sdk issue #117](https://github.com/tesserahq/tessera-sdk-py/issues/117)
so its interface can be driven by the first real provider migration rather than a
speculative snapshot format.

The JSON examples bundled under `tessera_sdk.mcp.fixtures` exercise the public
parser using the same payload shape emitted by controlled Python providers.

## Rules for future changes

- Keep metadata additive. Never move required model-facing data out of the normal
  MCP result and into `_meta`.
- Define reusable wire types, validation, limits, fixtures, and schemas here—not
  independently in Modela, a service, or a plugin.
- Keep domain semantics in the owning service. This SDK validates structure, not
  whether a `person.created` event is factually correct.
- Prefer new namespaced keys or optional fields for compatible extensions. A
  breaking meaning or shape requires an explicitly versioned contract.
- Treat debug data as potentially sensitive even when sanitized. Keep it bounded,
  opt-in, and authorization-gated.
- Preserve event compatibility with Tessera's existing `Event`/CloudEvent shape.
  Use the single `origin:*` tag to distinguish the MCP delivery path; do not add a
  parallel event vocabulary merely for completion clients.
- Update the Python models, parser fixtures, contract tests, and this guide
  together when the wire contract changes.
