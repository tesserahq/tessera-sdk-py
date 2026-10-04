import pytest

from tessera_sdk.mcp import get_origin, set_origin


def test_set_origin_replaces_existing_origin_and_preserves_other_tags():
    tags = set_origin(["audit", "origin:http-api"], "mcp")

    assert tags == ["audit", "origin:mcp"]


def test_get_origin_rejects_multiple_origin_tags():
    with pytest.raises(ValueError, match="At most one"):
        get_origin(["origin:mcp", "origin:http-api"])


def test_set_origin_rejects_empty_value():
    with pytest.raises(ValueError, match="non-empty"):
        set_origin([], "origin:")
