from pydantic import BaseModel, Field

from ....infra.events import Event
from ....mcp import ToolExecutionRecord


class ChatCompletionChunkExtensions(BaseModel):
    """Optional Modela extension carried by one streaming chunk."""

    event: Event | None = None
    tool_execution: ToolExecutionRecord | None = None


class ChatCompletionExtensions(BaseModel):
    """Optional Modela extensions returned by a non-streaming completion."""

    events: list[Event] = Field(default_factory=list)
    tool_executions: list[ToolExecutionRecord] = Field(default_factory=list)
