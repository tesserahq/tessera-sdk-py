"""Typed values shared by MCP providers, Modela, and completion clients."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictContractModel(BaseModel):
    """Base model that rejects undeclared fields in public wire contracts."""

    model_config = ConfigDict(extra="forbid")


class CompletionInclude(str, Enum):
    """Optional completion-response channels a caller may request."""

    EVENTS = "events"
    TOOL_EXECUTIONS = "tool_executions"


class ResourceReference(StrictContractModel):
    """Minimal, non-sensitive identity of a domain resource."""

    type: str = Field(min_length=1)
    id: str = Field(min_length=1)


class PublicEventData(StrictContractModel):
    """Client-safe projection carried by an MCP-originated domain event.

    It identifies the affected resource, optional related resources, and field
    names that changed. It intentionally excludes complete resource values.
    """

    resource: ResourceReference
    related: list[ResourceReference] = Field(default_factory=list)
    changed_fields: list[str] = Field(default_factory=list)


class ToolDebug(StrictContractModel):
    """Provider-selected diagnostic view of tool arguments and results.

    Providers must construct this projection deliberately; it is not permission
    to copy arbitrary tool inputs or outputs. Modela exposes it only through the
    separately authorized diagnostic channel.
    """

    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionStatus(str, Enum):
    """Lifecycle state recorded for one model-requested tool call."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    UNKNOWN = "unknown"


class ToolExecutionRecord(StrictContractModel):
    """Execution telemetry for one tool call in a completion.

    This records orchestration facts owned by Modela. It is distinct from
    provider events, which describe committed domain outcomes such as
    ``person.created``.
    """

    sequence: int = Field(ge=0)
    call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    status: ToolExecutionStatus
    duration_ms: float | None = Field(default=None, ge=0)
    debug: ToolDebug | None = None


class TruncationMarker(StrictContractModel):
    """Notice that a bounded completion-response channel omitted records."""

    channel: CompletionInclude
    truncated: Literal[True] = True
    dropped_count: int = Field(ge=1)
