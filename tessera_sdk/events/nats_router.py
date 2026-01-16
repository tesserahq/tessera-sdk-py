"""
FastStream NATS router and publishers for account-related events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from nats.aio.client import Client as NatsClient  # type: ignore[import]
from faststream.exceptions import IncorrectState  # type: ignore[import]
from faststream.nats.fastapi import NatsRouter  # type: ignore[import]

from tessera_sdk.config import get_settings
from tessera_sdk.events.event import Event

logger = logging.getLogger(__name__)
settings = get_settings()

nats_router = NatsRouter(settings.nats_url)


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
        """Ensure the broker connection is ready before publishing."""
        try:
            self._logger.debug("Ensuring NATS connection is ready")
            await nats_router.broker.connect()
            self._logger.debug("NATS connection ready")
        except IncorrectState:
            self._logger.warning("NATS connection in IncorrectState; resetting")
            await self._reset_connection()
            await nats_router.broker.connect()
        except Exception:
            self._logger.exception("NATS connect failed")
            raise

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
