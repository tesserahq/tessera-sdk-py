from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from tessera_sdk.events.event import Event
from tessera_sdk.events.nats_router import NatsEventPublisher


@pytest.fixture
def event():
    return Event(source="/api/test", event_type="com.example.created")


@pytest.mark.anyio
async def test_publish_skips_when_disabled(event):
    publisher = NatsEventPublisher()
    publisher._enabled = False

    with patch.object(publisher, "_publish_internal") as mock_publish:
        await publisher.publish(event, subject="topic")

    mock_publish.assert_not_called()


def test_publish_sync_uses_asyncio_run_when_no_loop(event):
    publisher = NatsEventPublisher()
    publisher._enabled = True

    with (
        patch(
            "tessera_sdk.events.nats_router.asyncio.get_running_loop",
            side_effect=RuntimeError,
        ),
        patch("tessera_sdk.events.nats_router.asyncio.run") as mock_run,
    ):
        publisher.publish_sync(event, subject="topic")

    args, _ = mock_run.call_args
    coro = args[0]
    assert coro.__name__ == "_publish_internal"
    coro.close()


@pytest.mark.anyio
async def test_publish_internal_retries_on_incorrect_state(event):
    publisher = NatsEventPublisher()
    publisher._enabled = True

    broker = SimpleNamespace(
        publish=AsyncMock(side_effect=[Exception("bad"), None]),
        connect=AsyncMock(),
        stop=AsyncMock(),
    )

    with (
        patch(
            "tessera_sdk.events.nats_router.nats_router", SimpleNamespace(broker=broker)
        ),
        patch("tessera_sdk.events.nats_router.IncorrectState", Exception),
    ):
        await publisher._publish_internal(event, subject="topic", close_after=True)

    assert broker.publish.call_count == 2


@pytest.mark.anyio
async def test_publish_internal_noop_when_disabled(event):
    publisher = NatsEventPublisher()
    publisher._enabled = False

    with patch("tessera_sdk.events.nats_router.nats_router") as mock_router:
        await publisher._publish_internal(event, subject="topic", close_after=False)

    mock_router.broker.publish.assert_not_called()


@pytest.mark.anyio
async def test_ensure_connection_handles_incorrect_state():
    publisher = NatsEventPublisher()
    publisher._enabled = True

    broker = SimpleNamespace(
        connect=AsyncMock(side_effect=[Exception("bad"), None]),
        stop=AsyncMock(),
    )

    with (
        patch(
            "tessera_sdk.events.nats_router.nats_router", SimpleNamespace(broker=broker)
        ),
        patch("tessera_sdk.events.nats_router.IncorrectState", Exception),
    ):
        await publisher._ensure_connection_ready()

    assert broker.connect.call_count == 2


@pytest.mark.anyio
async def test_reset_connection_ignores_incorrect_state():
    publisher = NatsEventPublisher()
    publisher._enabled = True

    broker = SimpleNamespace(stop=AsyncMock(side_effect=Exception("bad")))

    with (
        patch(
            "tessera_sdk.events.nats_router.nats_router", SimpleNamespace(broker=broker)
        ),
        patch("tessera_sdk.events.nats_router.IncorrectState", Exception),
    ):
        await publisher._reset_connection()

    broker.stop.assert_called_once()
