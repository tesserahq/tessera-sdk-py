from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompletionInclude(str, Enum):
    EVENTS = "events"
    TOOL_EXECUTIONS = "tool_executions"


class ResourceReference(StrictContractModel):
    type: str = Field(min_length=1)
    id: str = Field(min_length=1)


class PublicEventData(StrictContractModel):
    resource: ResourceReference
    related: list[ResourceReference] = Field(default_factory=list)
    changed_fields: list[str] = Field(default_factory=list)


class ToolDebug(StrictContractModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    UNKNOWN = "unknown"


class ToolExecutionRecord(StrictContractModel):
    sequence: int = Field(ge=0)
    call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    status: ToolExecutionStatus
    duration_ms: float | None = Field(default=None, ge=0)
    debug: ToolDebug | None = None


class TruncationMarker(StrictContractModel):
    channel: CompletionInclude
    truncated: Literal[True] = True
    dropped_count: int = Field(ge=1)
