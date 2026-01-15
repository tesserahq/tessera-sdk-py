from datetime import datetime
from types import SimpleNamespace

import pytest

from tessera_sdk.events.event import Event, event_source, event_type


def test_event_validates_required_fields():
    event = Event(source="/api/test", event_type="com.example.created")
    assert event.source == "/api/test"
    assert event.event_type == "com.example.created"


def test_event_invalid_source_raises():
    with pytest.raises(ValueError):
        Event(source="", event_type="com.example")


def test_event_invalid_type_raises():
    with pytest.raises(ValueError):
        Event(source="/api/test", event_type="")


def test_event_invalid_spec_version_raises():
    with pytest.raises(ValueError):
        Event(source="/api/test", event_type="com.example", spec_version="0.3")


def test_event_time_without_timezone():
    timestamp = datetime(2024, 1, 1)
    event = Event(source="/api/test", event_type="com.example", time=timestamp)
    assert event.time == timestamp


def test_event_helpers_use_settings(monkeypatch):
    settings = SimpleNamespace(event_type_prefix="com.test", event_source_prefix="src")
    monkeypatch.setattr("tessera_sdk.events.event.get_settings", lambda: settings)

    assert event_type("account.created") == "com.test.account.created"
    assert event_source("/accounts/1") == "/src/accounts/1"
