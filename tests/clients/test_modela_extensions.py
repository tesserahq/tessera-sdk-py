import json
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest
import requests
from pydantic import ValidationError

from tessera_sdk.clients._base.exceptions import (
    TesseraNotFoundError,
    TesseraServerError,
)
from tessera_sdk.clients.modela import (
    ModelaAuthenticationError,
    ModelaClient,
    ModelaClientError,
    ModelaError,
    ModelaNotFoundError,
    ModelaServerError,
    ModelaValidationError,
)
from tessera_sdk.clients.modela.schemas import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionMessage,
)
from tessera_sdk.infra.events import Event
from tessera_sdk.mcp import CompletionInclude, ToolExecutionRecord, TruncationMarker

EVENT = {
    "id": "event-1",
    "source": "/people",
    "event_type": "person.created",
    "time": "2026-10-05T10:00:00Z",
    "tags": ["origin:mcp"],
    "event_data": {"person_id": "person-1"},
}

TOOL_EXECUTION = {
    "sequence": 0,
    "call_id": "call-1",
    "tool_name": "people.create",
    "status": "completed",
    "duration_ms": 12.5,
}

RESPONSE = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "created": 1,
    "model": "model",
    "choices": [],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


def test_complete_sends_first_class_include_at_top_level():
    client = ModelaClient(base_url="https://modela.example.com")
    messages = [CompletionMessage(role="user", content="Create a person")]

    with patch.object(
        ModelaClient, "_make_request", return_value=Mock(json=lambda: RESPONSE)
    ) as request:
        client.complete(messages, include=[CompletionInclude.EVENTS])

    assert request.call_args.kwargs["data"]["include"] == ["events"]


def test_request_preserves_nested_legacy_include():
    request = ChatCompletionRequest(
        messages=[CompletionMessage(role="user", content="Hi")],
        extra_body={"include": ["events"]},
    )

    assert request.model_dump(mode="json", exclude_none=True)["extra_body"] == {
        "include": ["events"]
    }


def test_request_rejects_conflicting_include_sources():
    with pytest.raises(ValidationError, match="conflicts"):
        ChatCompletionRequest(
            messages=[CompletionMessage(role="user", content="Hi")],
            include=[CompletionInclude.EVENTS],
            extra_body={"include": ["tool_executions"]},
        )


def test_request_accepts_matching_include_sources():
    request = ChatCompletionRequest(
        messages=[CompletionMessage(role="user", content="Hi")],
        include=[CompletionInclude.EVENTS],
        extra_body={"include": ["events"]},
    )

    assert request.include == [CompletionInclude.EVENTS]


def test_non_streaming_response_parses_extensions():
    response = ChatCompletionResponse(
        **{
            **RESPONSE,
            "extensions": {
                "events": [EVENT],
                "tool_executions": [TOOL_EXECUTION],
            },
        }
    )

    assert response.extensions is not None
    assert response.extensions.events[0].event_type == "person.created"
    assert response.extensions.tool_executions[0].tool_name == "people.create"


def test_non_streaming_response_parses_one_truncation_per_channel():
    response = ChatCompletionResponse(
        **{
            **RESPONSE,
            "extensions": {
                "events": [EVENT],
                "truncations": [
                    {
                        "channel": "events",
                        "truncated": True,
                        "dropped_count": 2,
                    },
                    {
                        "channel": "tool_executions",
                        "truncated": True,
                        "dropped_count": 4,
                    },
                ],
            },
        }
    )

    assert response.extensions is not None
    assert [marker.channel for marker in response.extensions.truncations] == [
        CompletionInclude.EVENTS,
        CompletionInclude.TOOL_EXECUTIONS,
    ]
    assert all(
        isinstance(marker, TruncationMarker)
        for marker in response.extensions.truncations
    )


def test_non_streaming_response_keeps_first_marker_for_duplicate_channel(caplog):
    response = ChatCompletionResponse(
        **{
            **RESPONSE,
            "extensions": {
                "truncations": [
                    {
                        "channel": "events",
                        "truncated": True,
                        "dropped_count": 2,
                    },
                    {
                        "channel": "events",
                        "truncated": True,
                        "dropped_count": 8,
                    },
                ]
            },
        }
    )

    assert response.extensions is not None
    assert [marker.dropped_count for marker in response.extensions.truncations] == [2]
    assert "duplicate Modela completion truncation marker" in caplog.text


def test_non_streaming_response_drops_only_malformed_truncation_marker():
    response = ChatCompletionResponse(
        **{
            **RESPONSE,
            "extensions": {
                "events": [EVENT],
                "truncations": [
                    {
                        "channel": "events",
                        "truncated": False,
                        "dropped_count": 9,
                    },
                    {
                        "channel": "tool_executions",
                        "truncated": True,
                        "dropped_count": 4,
                    },
                ],
            },
        }
    )

    assert response.extensions is not None
    assert [event.id for event in response.extensions.events] == ["event-1"]
    assert [marker.channel for marker in response.extensions.truncations] == [
        CompletionInclude.TOOL_EXECUTIONS
    ]


@pytest.mark.anyio
async def test_streaming_chunk_preserves_empty_choices_event(monkeypatch):
    chunk = {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "model",
        "choices": [],
        "extensions": {"event": EVENT},
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, content=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n".encode()
        )
    )
    real_client = httpx.AsyncClient

    def client_with_transport(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(
        "tessera_sdk.clients.modela.client.httpx.AsyncClient",
        client_with_transport,
    )
    client = ModelaClient(base_url="https://modela.example.com")
    chunks = [
        chunk
        async for chunk in client.stream_complete(
            [CompletionMessage(role="user", content="Create a person")],
            include=[CompletionInclude.EVENTS],
        )
    ]

    assert chunks[0].choices == []
    assert chunks[0].extensions is not None
    assert chunks[0].extensions.event is not None
    assert chunks[0].extensions.event.id == "event-1"


@pytest.mark.anyio
async def test_streaming_chunk_parses_tool_execution(monkeypatch):
    chunk = {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "model",
        "choices": [],
        "extensions": {"tool_execution": TOOL_EXECUTION},
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, content=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n".encode()
        )
    )
    real_client = httpx.AsyncClient

    def client_with_transport(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(
        "tessera_sdk.clients.modela.client.httpx.AsyncClient",
        client_with_transport,
    )
    client = ModelaClient(base_url="https://modela.example.com")
    chunks = [
        item
        async for item in client.stream_complete(
            [CompletionMessage(role="user", content="Create a person")],
            include=[CompletionInclude.TOOL_EXECUTIONS],
        )
    ]

    assert chunks[0].extensions is not None
    assert chunks[0].extensions.tool_execution is not None
    assert chunks[0].extensions.tool_execution.call_id == "call-1"


@pytest.mark.anyio
async def test_streaming_chunk_parses_truncation_marker(monkeypatch):
    chunk = {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "model",
        "choices": [],
        "extensions": {
            "truncation": {
                "channel": "events",
                "truncated": True,
                "dropped_count": 3,
            }
        },
    }
    _patch_stream(monkeypatch, chunk)
    client = ModelaClient(base_url="https://modela.example.com")

    chunks = [
        item
        async for item in client.stream_complete(
            [CompletionMessage(role="user", content="Create a person")],
            include=[CompletionInclude.EVENTS],
        )
    ]

    assert chunks[0].extensions is not None
    assert chunks[0].extensions.truncation is not None
    assert chunks[0].extensions.truncation.channel is CompletionInclude.EVENTS
    assert chunks[0].extensions.truncation.dropped_count == 3


def test_completion_error_exposes_committed_events():
    response = requests.Response()
    response.status_code = 500
    response.url = "https://modela.example.com/chat/completions"
    response._content = json.dumps(
        {"detail": "provider failed", "extensions": {"events": [EVENT]}}
    ).encode()
    response.headers["Content-Type"] = "application/json"
    session = Mock()
    session.headers = {}
    session.request.return_value = response
    client = ModelaClient(base_url="https://modela.example.com", session=session)

    with pytest.raises(ModelaServerError) as error:
        client.complete([CompletionMessage(role="user", content="Create a person")])

    assert error.value.events[0].id == "event-1"


def test_completion_error_exposes_event_truncation_marker():
    response = requests.Response()
    response.status_code = 500
    response.url = "https://modela.example.com/chat/completions"
    response._content = json.dumps(
        {
            "detail": "provider failed",
            "extensions": {
                "events": [EVENT],
                "truncations": [
                    {
                        "channel": "events",
                        "truncated": True,
                        "dropped_count": 2,
                    }
                ],
            },
        }
    ).encode()
    response.headers["Content-Type"] = "application/json"
    session = Mock()
    session.headers = {}
    session.request.return_value = response
    client = ModelaClient(base_url="https://modela.example.com", session=session)

    with pytest.raises(ModelaServerError) as error:
        client.complete([CompletionMessage(role="user", content="Create a person")])

    assert error.value.truncations[0].channel is CompletionInclude.EVENTS
    assert error.value.truncations[0].dropped_count == 2


@pytest.mark.anyio
async def test_streaming_error_exposes_unknown_domain_event_type(monkeypatch):
    unknown_event = {**EVENT, "event_type": "household.archived"}
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            500,
            json={
                "detail": "provider failed after commit",
                "extensions": {"events": [unknown_event]},
            },
        )
    )
    real_client = httpx.AsyncClient

    def client_with_transport(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(
        "tessera_sdk.clients.modela.client.httpx.AsyncClient",
        client_with_transport,
    )
    client = ModelaClient(base_url="https://modela.example.com")

    with pytest.raises(ModelaServerError) as error:
        async for _ in client.stream_complete(
            [CompletionMessage(role="user", content="Archive household")],
            include=[CompletionInclude.EVENTS],
        ):
            pass

    assert error.value.events[0].event_type == "household.archived"


MALFORMED_EVENT = {**EVENT, "id": "event-bad", "tags": "origin:mcp"}

TRUNCATION_MARKER = {
    "channel": "tool_executions",
    "truncated": True,
    "dropped_count": 3,
}


def _chunk(**extra):
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "model",
        "choices": [],
        **extra,
    }


def _text_chunk(content):
    return _chunk(
        choices=[{"index": 0, "delta": {"content": content}, "finish_reason": None}]
    )


def _patch_stream(monkeypatch, *chunks):
    body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=f"{body}data: [DONE]\n".encode())
    )
    real_client = httpx.AsyncClient

    def client_with_transport(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(
        "tessera_sdk.clients.modela.client.httpx.AsyncClient",
        client_with_transport,
    )


@pytest.mark.anyio
async def test_streaming_survives_unreadable_extensions(monkeypatch):
    _patch_stream(
        monkeypatch,
        _text_chunk("Creating "),
        _chunk(extensions={"event": MALFORMED_EVENT}),
        _chunk(extensions={"tool_execution": TRUNCATION_MARKER}),
        _chunk(extensions=["not", "an", "object"]),
        _text_chunk("Jane."),
    )
    client = ModelaClient(base_url="https://modela.example.com")

    chunks = [
        chunk
        async for chunk in client.stream_complete(
            [CompletionMessage(role="user", content="Create Jane")],
            include=[CompletionInclude.EVENTS, CompletionInclude.TOOL_EXECUTIONS],
        )
    ]

    text = "".join(c.choices[0].delta.content for c in chunks if c.choices)
    assert text == "Creating Jane."
    assert chunks[1].extensions is not None
    assert chunks[1].extensions.event is None
    assert chunks[2].extensions is not None
    assert chunks[2].extensions.tool_execution is None
    assert chunks[3].extensions is None


def test_malformed_truncation_does_not_hide_neighboring_event():
    chunk = ChatCompletionChunk(
        **_chunk(
            extensions={
                "event": EVENT,
                "truncation": {
                    "channel": "events",
                    "truncated": False,
                    "dropped_count": 3,
                },
            }
        )
    )

    assert chunk.extensions is not None
    assert chunk.extensions.event is not None
    assert chunk.extensions.event.id == "event-1"
    assert chunk.extensions.truncation is None


def test_truncation_marker_ignores_fields_added_by_newer_modela():
    chunk = ChatCompletionChunk(
        **_chunk(
            extensions={
                "truncation": {
                    "channel": "events",
                    "truncated": True,
                    "dropped_count": 3,
                    "budget_bytes": 262144,
                }
            }
        )
    )

    assert chunk.extensions is not None
    assert chunk.extensions.truncation is not None
    assert chunk.extensions.truncation.dropped_count == 3


def test_tool_execution_ignores_fields_added_by_newer_modela():
    record = {
        **TOOL_EXECUTION,
        "error_category": "timeout",
        "debug": {"arguments": {}, "result": {}, "redacted": True},
    }

    chunk = ChatCompletionChunk(**_chunk(extensions={"tool_execution": record}))

    assert chunk.extensions is not None
    assert chunk.extensions.tool_execution is not None
    assert chunk.extensions.tool_execution.call_id == "call-1"
    assert isinstance(chunk.extensions.tool_execution, ToolExecutionRecord)


def test_non_streaming_response_keeps_valid_records_and_drops_invalid_ones():
    response = ChatCompletionResponse(
        **{
            **RESPONSE,
            "extensions": {
                "events": [EVENT, MALFORMED_EVENT],
                "tool_executions": [TOOL_EXECUTION, TRUNCATION_MARKER],
            },
        }
    )

    assert response.extensions is not None
    assert [e.id for e in response.extensions.events] == ["event-1"]
    assert [t.call_id for t in response.extensions.tool_executions] == ["call-1"]


@pytest.mark.parametrize(
    ("fixture_name", "model"),
    [
        ("truncation_chunk.json", ChatCompletionChunk),
        ("truncated_completion_response.json", ChatCompletionResponse),
    ],
)
def test_documented_truncation_fixtures_match_public_models(fixture_name, model):
    fixture_path = (
        Path(__file__).parents[2]
        / "tessera_sdk"
        / "clients"
        / "modela"
        / "fixtures"
        / fixture_name
    )

    parsed = model.model_validate_json(fixture_path.read_text())

    assert parsed.extensions is not None


def test_completion_error_keeps_valid_events_when_one_is_malformed():
    response = requests.Response()
    response.status_code = 502
    response.url = "https://modela.example.com/chat/completions"
    response._content = json.dumps(
        {
            "detail": "provider failed",
            "extensions": {
                "events": [EVENT, MALFORMED_EVENT],
                "tool_executions": [TRUNCATION_MARKER],
            },
        }
    ).encode()
    response.headers["Content-Type"] = "application/json"
    session = Mock()
    session.headers = {}
    session.request.return_value = response
    client = ModelaClient(base_url="https://modela.example.com", session=session)

    with pytest.raises(ModelaError) as error:
        client.complete([CompletionMessage(role="user", content="Create a person")])

    assert [e.id for e in error.value.events] == ["event-1"]


@pytest.mark.parametrize(
    ("error_type", "status_code"),
    [
        (ModelaClientError, 409),
        (ModelaServerError, 502),
        (ModelaAuthenticationError, 401),
        (ModelaNotFoundError, 404),
        (ModelaValidationError, 400),
    ],
)
def test_every_modela_error_is_catchable_as_modela_error(error_type, status_code):
    error = error_type("failed", status_code, events=[Event(**EVENT)])

    assert isinstance(error, ModelaError)
    assert error.status_code == status_code
    assert error.events[0].id == "event-1"


def test_modela_errors_keep_their_tessera_base_types():
    assert issubclass(ModelaServerError, TesseraServerError)
    assert issubclass(ModelaNotFoundError, TesseraNotFoundError)
    assert ModelaNotFoundError().status_code == 404


@pytest.mark.parametrize(
    "nested",
    [["tool_executions", "events"], ("events", "tool_executions", "events")],
)
def test_request_accepts_same_include_channels_in_any_order_or_container(nested):
    request = ChatCompletionRequest(
        messages=[CompletionMessage(role="user", content="Hi")],
        include=[CompletionInclude.EVENTS, CompletionInclude.TOOL_EXECUTIONS],
        extra_body={"include": nested},
    )

    assert request.include == [
        CompletionInclude.EVENTS,
        CompletionInclude.TOOL_EXECUTIONS,
    ]


@pytest.fixture
def anyio_backend():
    return "asyncio"
