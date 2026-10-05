import pytest

from tessera_sdk.mcp import (
    MCP_EVENTS_META_KEY,
    MCPMetadataError,
    MetadataLimits,
    load_contract_fixture,
    parse_mcp_metadata,
)

VALID_EVENT = {
    "id": "event-123",
    "source": "/tests",
    "event_type": "person.created",
    "time": "2026-01-15T10:30:00Z",
    "tags": ["origin:mcp"],
    "event_data": {"person_id": "person-123"},
}


def test_parse_canonical_metadata_fixture():
    metadata = parse_mcp_metadata(load_contract_fixture("valid_metadata.json"))

    assert metadata.events[0].event_type == "person.created"
    assert metadata.events[0].tags == ["origin:mcp"]
    assert metadata.debug is not None
    assert metadata.debug.result == {"person_id": "person-123"}


def test_parse_metadata_ignores_unknown_namespaced_keys():
    metadata = parse_mcp_metadata({"vendor.example/value": {"ok": True}})

    assert metadata.events == []
    assert metadata.debug is None


def test_parse_metadata_rejects_unnamespaced_tessera_aliases():
    with pytest.raises(MCPMetadataError, match="namespaced") as error:
        parse_mcp_metadata({"events": []})

    assert error.value.code == "unnamespaced_key"


def test_parse_metadata_treats_null_events_as_empty():
    metadata = parse_mcp_metadata({MCP_EVENTS_META_KEY: None})

    assert metadata.events == []


def test_parse_metadata_rejects_event_without_origin():
    event = {**VALID_EVENT, "tags": []}

    with pytest.raises(MCPMetadataError, match="contract") as error:
        parse_mcp_metadata({MCP_EVENTS_META_KEY: [event]})

    assert error.value.code == "invalid_contract"


def test_parse_metadata_requires_mcp_origin():
    event = {**VALID_EVENT, "tags": ["origin:http-api"]}

    with pytest.raises(MCPMetadataError) as error:
        parse_mcp_metadata({MCP_EVENTS_META_KEY: [event]})

    assert error.value.code == "invalid_contract"


def test_parse_metadata_rejects_multiple_origins_fixture():
    with pytest.raises(MCPMetadataError) as error:
        parse_mcp_metadata(load_contract_fixture("invalid_multiple_origins.json"))

    assert error.value.code == "invalid_contract"


@pytest.mark.parametrize("missing", ["id", "time"])
def test_parse_metadata_requires_transport_stable_event_identity(missing):
    event = {key: value for key, value in VALID_EVENT.items() if key != missing}

    with pytest.raises(MCPMetadataError) as error:
        parse_mcp_metadata({MCP_EVENTS_META_KEY: [event]})

    assert error.value.code == "invalid_contract"


@pytest.mark.parametrize("event_data", ["private", b"private", ["private"]])
def test_parse_metadata_requires_object_shaped_event_data(event_data):
    event = {**VALID_EVENT, "event_data": event_data}

    with pytest.raises(MCPMetadataError) as error:
        parse_mcp_metadata({MCP_EVENTS_META_KEY: [event]})

    assert error.value.code == "invalid_contract"


def test_parse_metadata_enforces_event_count_limit():
    with pytest.raises(MCPMetadataError, match="count") as error:
        parse_mcp_metadata(
            {MCP_EVENTS_META_KEY: [{}, {}]},
            MetadataLimits(max_events=1),
        )

    assert error.value.code == "event_count_exceeded"


def test_parse_metadata_enforces_depth_limit():
    with pytest.raises(MCPMetadataError, match="depth") as error:
        parse_mcp_metadata(
            {MCP_EVENTS_META_KEY: [[[["too-deep"]]]]},
            MetadataLimits(max_depth=2),
        )

    assert error.value.code == "events_depth_exceeded"


def test_parse_metadata_uses_one_public_error_type_for_invalid_container():
    with pytest.raises(MCPMetadataError) as error:
        parse_mcp_metadata([])  # type: ignore[arg-type]

    assert error.value.code == "invalid_container"


def test_parse_metadata_uses_one_public_error_type_for_invalid_events_type():
    with pytest.raises(MCPMetadataError) as error:
        parse_mcp_metadata({MCP_EVENTS_META_KEY: {}})

    assert error.value.code == "invalid_events_type"


def test_parse_metadata_enforces_total_event_byte_limit():
    with pytest.raises(MCPMetadataError) as error:
        parse_mcp_metadata(
            {MCP_EVENTS_META_KEY: [VALID_EVENT]},
            MetadataLimits(max_total_event_bytes=1),
        )

    assert error.value.code == "events_bytes_exceeded"
