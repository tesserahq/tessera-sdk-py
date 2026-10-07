import logging
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidatorFunctionWrapHandler,
    field_validator,
)

from ....infra.events import Event
from ....mcp import ToolDebug, ToolExecutionRecord, TruncationMarker

logger = logging.getLogger(__name__)


# Extensions are best-effort metadata: a record the SDK cannot read must never
# cost the caller the completion itself. Invalid records are dropped and logged
# by error type only, because their values may contain sensitive data.


class _ToolDebugView(ToolDebug):
    """Read-side ``ToolDebug`` that ignores fields added by newer Modela versions."""

    model_config = ConfigDict(extra="ignore")


class _ToolExecutionRecordView(ToolExecutionRecord):
    """Read-side ``ToolExecutionRecord`` that ignores unknown fields.

    The provider-side contract forbids undeclared fields; a client must instead
    tolerate fields a newer Modela adds.
    """

    model_config = ConfigDict(extra="ignore")

    debug: _ToolDebugView | None = None


class _TruncationMarkerView(TruncationMarker):
    """Read-side marker that tolerates fields added by newer Modela versions."""

    model_config = ConfigDict(extra="ignore")


def _log_dropped(field: str, error: ValidationError) -> None:
    logger.warning(
        "Dropped invalid Modela completion extension %s: %s",
        field,
        sorted({err["type"] for err in error.errors(include_input=False)}),
    )


def _validate_optional(
    field: str, value: Any, handler: ValidatorFunctionWrapHandler
) -> Any:
    try:
        return handler(value)
    except ValidationError as e:
        _log_dropped(field, e)
        return None


def _validate_items(
    field: str, value: Any, handler: ValidatorFunctionWrapHandler
) -> list[Any]:
    if not isinstance(value, list):
        logger.warning(
            "Dropped invalid Modela completion extension %s: not a list", field
        )
        return []
    valid = []
    for item in value:
        try:
            valid.extend(handler([item]))
        except ValidationError as e:
            _log_dropped(field, e)
    return valid


class ChatCompletionChunkExtensions(BaseModel):
    """Optional Modela extension carried by one streaming chunk.

    A truncation marker is sent in its own empty-choice chunk after the final
    retained record for its channel. It is not mixed into the event or tool
    execution record types.
    """

    event: Event | None = None
    tool_execution: _ToolExecutionRecordView | None = None
    truncation: _TruncationMarkerView | None = None

    @field_validator("event", "tool_execution", "truncation", mode="wrap")
    @classmethod
    def _drop_invalid(cls, value, handler, info):
        return _validate_optional(info.field_name, value, handler)


class ChatCompletionExtensions(BaseModel):
    """Extensions returned by a non-streaming completion or error response.

    ``truncations`` contains at most one marker per channel. Each corresponding
    record list is the retained prefix; ``dropped_count`` reports later records
    omitted by the producer's response budget.
    """

    events: list[Event] = Field(default_factory=list)
    tool_executions: list[_ToolExecutionRecordView] = Field(default_factory=list)
    truncations: list[_TruncationMarkerView] = Field(default_factory=list)

    @field_validator("events", "tool_executions", "truncations", mode="wrap")
    @classmethod
    def _drop_invalid_items(cls, value, handler, info):
        return _validate_items(info.field_name, value, handler)

    @field_validator("truncations", mode="after")
    @classmethod
    def _keep_one_marker_per_channel(cls, markers):
        unique = []
        seen_channels = set()
        for marker in markers:
            if marker.channel in seen_channels:
                logger.warning(
                    "Dropped duplicate Modela completion truncation marker "
                    "for channel %s",
                    marker.channel.value,
                )
                continue
            seen_channels.add(marker.channel)
            unique.append(marker)
        return unique
