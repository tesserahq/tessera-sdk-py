# Modela completion-extension fixtures

These fixtures document the SDK-owned wire position of completion-channel
truncation markers. They contain synthetic values only and are parsed by the
public SDK response models in the test suite.

- `truncation_chunk.json` shows a streaming marker in
  `extensions.truncation`. Modela emits this empty-choice chunk after the final
  retained record for the named channel.
- `truncated_completion_response.json` shows the plural
  `extensions.truncations` collection used by non-streaming and error
  responses. It contains at most one marker for each channel.

Markers are deliberately separate from `events` and `tool_executions`; those
collections remain homogeneous. A marker means the corresponding records are
the retained prefix and `dropped_count` later records were omitted.
