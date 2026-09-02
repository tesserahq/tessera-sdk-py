import json

import httpx
import pytest

from tessera_sdk.clients._base.exceptions import (
    TesseraAuthenticationError,
    TesseraError,
)
from tessera_sdk.clients.modela import ModelaClient
from tessera_sdk.clients.modela.schemas import CompletionMessage


def _sse_body(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode()


def _patch_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(
        "tessera_sdk.clients.modela.client.httpx.AsyncClient", fake_async_client
    )


CHUNK_1 = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "created": 1,
    "model": "openai-gpt-4o",
    "choices": [
        {
            "index": 0,
            "delta": {"role": "assistant", "content": "Hel"},
            "finish_reason": None,
        }
    ],
}
CHUNK_2 = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "created": 1,
    "model": "openai-gpt-4o",
    "choices": [{"index": 0, "delta": {"content": "lo"}, "finish_reason": None}],
}
CHUNK_FINAL = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "created": 1,
    "model": "openai-gpt-4o",
    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
}


@pytest.mark.anyio
async def test_stream_complete_yields_parsed_chunks_in_order(monkeypatch):
    sse = _sse_body(
        [
            f"data: {json.dumps(CHUNK_1)}",
            "",
            f"data: {json.dumps(CHUNK_2)}",
            "",
            f"data: {json.dumps(CHUNK_FINAL)}",
            "",
            "data: [DONE]",
            "",
        ]
    )

    def handler(request):
        return httpx.Response(200, content=sse)

    _patch_transport(monkeypatch, handler)

    client = ModelaClient(base_url="https://modela.example.com", api_token="tok")
    messages = [CompletionMessage(role="user", content="Hi")]

    chunks = [c async for c in client.stream_complete(messages=messages)]

    contents = [c.choices[0].delta.content for c in chunks]
    assert contents == ["Hel", "lo", None]
    assert chunks[-1].choices[0].finish_reason == "stop"


@pytest.mark.anyio
async def test_stream_complete_sets_stream_true_and_omits_model_by_default(
    monkeypatch,
):
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, content=_sse_body(["data: [DONE]", ""]))

    _patch_transport(monkeypatch, handler)

    client = ModelaClient(base_url="https://modela.example.com", api_token="tok")
    messages = [CompletionMessage(role="user", content="Hi")]

    async for _ in client.stream_complete(messages=messages):
        pass

    assert captured["body"]["stream"] is True
    assert "model" not in captured["body"]


@pytest.mark.anyio
async def test_stream_complete_ends_cleanly_without_done_sentinel(monkeypatch):
    sse = _sse_body([f"data: {json.dumps(CHUNK_1)}", ""])

    def handler(request):
        return httpx.Response(200, content=sse)

    _patch_transport(monkeypatch, handler)

    client = ModelaClient(base_url="https://modela.example.com", api_token="tok")
    messages = [CompletionMessage(role="user", content="Hi")]

    chunks = [c async for c in client.stream_complete(messages=messages)]

    assert len(chunks) == 1
    assert chunks[0].choices[0].delta.content == "Hel"


@pytest.mark.anyio
async def test_stream_complete_raises_on_malformed_chunk(monkeypatch):
    sse = _sse_body(["data: {not valid json", ""])

    def handler(request):
        return httpx.Response(200, content=sse)

    _patch_transport(monkeypatch, handler)

    client = ModelaClient(base_url="https://modela.example.com", api_token="tok")
    messages = [CompletionMessage(role="user", content="Hi")]

    with pytest.raises(TesseraError):
        async for _ in client.stream_complete(messages=messages):
            pass


@pytest.mark.anyio
async def test_stream_complete_raises_on_auth_error(monkeypatch):
    def handler(request):
        return httpx.Response(401, json={"detail": "unauthorized"})

    _patch_transport(monkeypatch, handler)

    client = ModelaClient(base_url="https://modela.example.com", api_token="tok")
    messages = [CompletionMessage(role="user", content="Hi")]

    with pytest.raises(TesseraAuthenticationError):
        async for _ in client.stream_complete(messages=messages):
            pass


@pytest.fixture
def anyio_backend():
    return "asyncio"
