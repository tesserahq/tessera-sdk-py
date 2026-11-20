from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from tessera_sdk.infra.events.event import Event
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


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
            "tessera_sdk.infra.events.nats_router.asyncio.get_running_loop",
            side_effect=RuntimeError,
        ),
        patch("tessera_sdk.infra.events.nats_router.asyncio.run") as mock_run,
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
            "tessera_sdk.infra.events.nats_router.nats_router",
            SimpleNamespace(broker=broker),
        ),
        patch("tessera_sdk.infra.events.nats_router.IncorrectState", Exception),
    ):
        await publisher._publish_internal(event, subject="topic", close_after=True)

    assert broker.publish.call_count == 2


@pytest.mark.anyio
async def test_publish_internal_noop_when_disabled(event):
    publisher = NatsEventPublisher()
    publisher._enabled = False

    with patch("tessera_sdk.infra.events.nats_router.nats_router") as mock_router:
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
            "tessera_sdk.infra.events.nats_router.nats_router",
            SimpleNamespace(broker=broker),
        ),
        patch("tessera_sdk.infra.events.nats_router.IncorrectState", Exception),
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
            "tessera_sdk.infra.events.nats_router.nats_router",
            SimpleNamespace(broker=broker),
        ),
        patch("tessera_sdk.infra.events.nats_router.IncorrectState", Exception),
    ):
        await publisher._reset_connection()

    broker.stop.assert_called_once()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "message",
    ["nats: Authorization Violation", "nats: 'Authorization Violation'"],
)
async def test_error_callback_aborts_on_authorization_violation(message):
    from nats.errors import Error as NatsError

    from tessera_sdk.infra.events.nats_router import _raise_unrecoverable

    with pytest.raises(NatsError):
        await _raise_unrecoverable(NatsError(message))


@pytest.mark.anyio
@pytest.mark.parametrize(
    "err",
    [ConnectionResetError("reset"), TimeoutError()],
)
async def test_error_callback_lets_transient_errors_retry(err):
    from tessera_sdk.infra.events.nats_router import _raise_unrecoverable

    await _raise_unrecoverable(err)


@pytest.mark.anyio
async def test_error_callback_lets_transient_nats_errors_retry():
    from nats.errors import Error as NatsError

    from tessera_sdk.infra.events.nats_router import _raise_unrecoverable

    await _raise_unrecoverable(NatsError("nats: stale connection"))


def test_router_registers_error_callback():
    from tessera_sdk.infra.events.nats_router import nats_router

    # faststream wraps the callback; it must still reach nats-py's connect.
    assert nats_router.broker._connection_kwargs["error_cb"] is not None


@pytest.mark.anyio
async def test_publish_sync_keeps_background_task_alive(event):
    import asyncio
    import importlib

    module = importlib.import_module("tessera_sdk.infra.events.nats_router")

    publisher = NatsEventPublisher()
    publisher._enabled = True
    release = asyncio.Event()

    async def slow_publish(*_args, **_kwargs):
        await release.wait()

    with patch.object(publisher, "_publish_internal", side_effect=slow_publish):
        publisher.publish_sync(event, subject="topic")
        await asyncio.sleep(0)
        assert len(module._background_tasks) == 1

        release.set()
        await asyncio.sleep(0.01)

    assert module._background_tasks == set()


@pytest.mark.anyio
async def test_ensure_connection_times_out_and_resets(caplog):
    import asyncio

    publisher = NatsEventPublisher()
    publisher._enabled = True

    async def hang():
        await asyncio.sleep(60)

    broker = SimpleNamespace(connect=hang, stop=AsyncMock())

    with (
        patch(
            "tessera_sdk.infra.events.nats_router.nats_router",
            SimpleNamespace(broker=broker),
        ),
        patch(
            "tessera_sdk.infra.events.nats_router.settings.nats_connect_timeout",
            0.05,
        ),
        pytest.raises(TimeoutError),
    ):
        await publisher._ensure_connection_ready()

    broker.stop.assert_awaited_once()
    assert "no connection within 0.05s" in caplog.text
