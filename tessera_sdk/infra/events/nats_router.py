"""
FastStream NATS router and publishers for account-related events.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from faststream.exceptions import IncorrectState  # type: ignore[import]
from faststream.nats.fastapi import NatsRouter  # type: ignore[import]
from nats.errors import Error as NatsError  # type: ignore[import]

from ...config import get_settings
from .event import Event

logger = logging.getLogger(__name__)
settings = get_settings()

# Server errors that retrying cannot fix. nats-py treats them as transient and
# keeps cycling through the cluster, so a wrong password surfaces minutes later
# as a misleading NoServersError. (faststream 0.7.8+ has the same list; older
# releases don't, so the SDK enforces it itself.)
UNRECOVERABLE_CONNECT_ERRORS = frozenset(
    {
        "authorization violation",
        "authorization timeout",
        "invalid client protocol",
        "user authentication expired",
        "user authentication revoked",
        "account authentication expired",
    }
)


async def _raise_unrecoverable(err: Exception) -> None:
    """nats-py error callback: abort connecting on errors retries cannot fix."""
    if isinstance(err, NatsError):
        reason = str(err).removeprefix("nats: ").strip("'").lower()
        if reason in UNRECOVERABLE_CONNECT_ERRORS:
            raise err


nats_router = NatsRouter(settings.nats_url, error_cb=_raise_unrecoverable)

# asyncio keeps only weak references to tasks; hold fire-and-forget publishes
# until they finish so they are not garbage-collected mid-flight.
_background_tasks: set[asyncio.Task] = set()


class NatsEventPublisher:
    """Publish account events to NATS using FastStream."""

    def __init__(self):
        self._enabled = settings.nats_enabled
        self._logger = logger
        if not self._enabled:
            self._logger.warning("NATS publishing is DISABLED by configuration")

    async def publish(self, event: Event, subject: str) -> None:
        """Publish an event to NATS."""
        if not self._enabled:
            self._logger.info(
                f"NATS publishing disabled; skipping event: {event.event_type}"
            )
            return

        await self._publish_internal(event, subject, close_after=False)

    def publish_sync(self, event: Event, subject: str) -> None:
        """Synchronously publish an event to NATS."""
        if not self._enabled:
            self._logger.info(
                f"NATS publishing disabled; skipping event: {event.event_type}"
            )
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._logger.info(
                f"NATS publishing event: {event.event_type} using asyncio.run"
            )
            asyncio.run(self._publish_internal(event, subject, close_after=True))
        else:
            self._logger.info(
                f"NATS publishing event: {event.event_type} using background task"
            )
            task = loop.create_task(
                self._publish_internal(event, subject, close_after=False)
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)

            def _log_task_result(t: asyncio.Task) -> None:
                exc = t.exception()
                if exc:
                    self._logger.exception(
                        "Background NATS publish task failed",
                        exc_info=exc,
                        extra={
                            "event_type": event.event_type,
                            "subject": subject,
                        },
                    )

            task.add_done_callback(_log_task_result)

    async def _publish_internal(
        self, event: Event, subject: str, close_after: bool
    ) -> None:
        """Publish an event, optionally closing the connection afterwards."""
        if not self._enabled:
            return

        await self._ensure_connection_ready()
        self._logger.info(
            "NATS publish attempt",
            extra={
                "event_type": event.event_type,
                "subject": subject,
                "event_id": event.id,
            },
        )
        try:
            await nats_router.broker.publish(
                event.model_dump(mode="json"), subject=subject
            )
            self._logger.info(
                "NATS publish succeeded",
                extra={
                    "event_type": event.event_type,
                    "subject": subject,
                    "event_id": event.id,
                },
            )
        except IncorrectState:
            self._logger.warning(
                "NATS publish failed due to IncorrectState; resetting connection",
                extra={"event_type": event.event_type, "subject": subject},
            )
            await self._reset_connection()
            await self._ensure_connection_ready()
            await nats_router.broker.publish(
                event.model_dump(mode="json"), subject=subject
            )
        except Exception:
            self._logger.exception(
                "NATS publish failed",
                extra={
                    "event_type": event.event_type,
                    "subject": subject,
                    "event_id": event.id,
                },
            )
            raise
        finally:
            if close_after:
                await self._reset_connection()

    async def _ensure_connection_ready(self) -> None:
        """Ensure the broker connection is ready before publishing.

        Bounded by ``nats_connect_timeout``: without it, an unreachable server
        holds the publish for minutes while nats-py retries.
        """
        timeout = settings.nats_connect_timeout
        try:
            self._logger.debug("Ensuring NATS connection is ready")
            try:
                await asyncio.wait_for(nats_router.broker.connect(), timeout)
            except IncorrectState:
                self._logger.warning("NATS connection in IncorrectState; resetting")
                await self._reset_connection()
                await asyncio.wait_for(nats_router.broker.connect(), timeout)
            self._logger.debug("NATS connection ready")
        except TimeoutError:
            self._logger.error("NATS connect failed: no connection within %ss", timeout)
            await self._reset_connection_quietly()
            raise
        except Exception as e:
            # The reason goes in the message: it's the error tracker's title.
            reason = str(e) or type(e).__name__
            self._logger.exception("NATS connect failed: %s", reason)
            raise

    async def _reset_connection_quietly(self) -> None:
        """Reset after a failed connect without masking the original error."""
        with contextlib.suppress(Exception):  # _reset_connection logs it
            await self._reset_connection()

    async def _reset_connection(self) -> None:
        """Close and reset the broker connection state."""
        try:
            self._logger.warning("Resetting NATS connection")
            await nats_router.broker.stop()
        except IncorrectState:
            # Connection already reset; nothing else to do.
            return
        except Exception:
            self._logger.exception("NATS reset failed")
            raise
