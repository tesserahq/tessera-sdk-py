import pytest
from pydantic import ValidationError

from tessera_sdk.mcp import (
    MCP_EVENTS_META_KEY,
    MetadataLimits,
    load_contract_fixture,
    parse_mcp_metadata,
)


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
    with pytest.raises(ValueError, match="namespaced"):
        parse_mcp_metadata({"events": []})


def test_parse_metadata_rejects_event_without_origin():
    event = {
        "source": "/tests",
        "event_type": "person.created",
        "tags": [],
    }

    with pytest.raises(ValidationError, match="origin"):
        parse_mcp_metadata({MCP_EVENTS_META_KEY: [event]})


def test_parse_metadata_rejects_multiple_origins_fixture():
    with pytest.raises(ValidationError, match="At most one"):
        parse_mcp_metadata(load_contract_fixture("invalid_multiple_origins.json"))


def test_parse_metadata_enforces_event_count_limit():
    with pytest.raises(ValueError, match="count"):
        parse_mcp_metadata(
            {MCP_EVENTS_META_KEY: [{}, {}]},
            MetadataLimits(max_events=1),
        )


def test_parse_metadata_enforces_depth_limit():
    with pytest.raises(ValueError, match="depth"):
        parse_mcp_metadata(
            {MCP_EVENTS_META_KEY: [[[["too-deep"]]]]},
            MetadataLimits(max_depth=2),
        )
