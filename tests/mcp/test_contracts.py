import pytest
from pydantic import ValidationError

from tessera_sdk.mcp import (
    CompletionInclude,
    PublicEventData,
    ResourceReference,
    ToolExecutionRecord,
    ToolExecutionStatus,
    TruncationMarker,
    contract_json_schemas,
    load_contract_schema,
)


def test_public_event_data_rejects_unreviewed_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        PublicEventData(
            resource=ResourceReference(type="person", id="person-1"),
            email="private@example.com",
        )


def test_tool_execution_rejects_negative_duration():
    with pytest.raises(ValidationError, match="greater_than_equal"):
        ToolExecutionRecord(
            sequence=1,
            call_id="call-1",
            tool_name="people.create",
            status=ToolExecutionStatus.COMPLETED,
            duration_ms=-1,
        )


def test_truncation_marker_uses_completion_channel():
    marker = TruncationMarker(
        channel=CompletionInclude.EVENTS,
        dropped_count=3,
    )

    assert marker.model_dump(mode="json") == {
        "channel": "events",
        "truncated": True,
        "dropped_count": 3,
    }


def test_contract_schema_bundle_contains_public_models():
    schemas = contract_json_schemas()

    assert set(schemas) == {
        "MCPMetadata",
        "PublicEventData",
        "ResourceReference",
        "ToolDebug",
        "ToolExecutionRecord",
        "TruncationMarker",
    }


def test_language_neutral_schema_is_bundled():
    schema = load_contract_schema()

    assert schema["$id"] == "https://schemas.tessera.dev/mcp/metadata/v1"
    assert "com.tesserahq/events" in schema["properties"]
