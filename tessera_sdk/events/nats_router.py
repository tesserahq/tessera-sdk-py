"""
FastStream NATS router and publishers for account-related events.
"""

from __future__ import annotations

import asyncio
import logging

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
            self._logger.info(f"NATS publishing event: {event.event_type}")
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._logger.info(
                f"NATS publishing event: {event.event_type} using asyncio.run"
            )
            asyncio.run(self._publish_internal(event, subject, close_after=True))
        else:
            self._logger.info(
                f"NATS publishing event: {event.event_type} using loop.create_task"
            )
            loop.create_task(self.publish(event, subject))

    async def _publish_internal(
        self, event: Event, subject: str, close_after: bool
    ) -> None:
        """Publish an event, optionally closing the connection afterwards."""
        if not self._enabled:
            return

        await self._ensure_connection_ready()
        try:
            await nats_router.broker.publish(
                event.model_dump(mode="json"), subject=subject
            )
        except IncorrectState:
            await self._reset_connection()
            await self._ensure_connection_ready()
            await nats_router.broker.publish(
                event.model_dump(mode="json"), subject=subject
            )
        finally:
            if close_after:
                await self._reset_connection()

    async def _ensure_connection_ready(self) -> None:
        """Ensure the broker connection is ready before publishing."""
        try:
            await nats_router.broker.connect()
        except IncorrectState:
            await self._reset_connection()
            await nats_router.broker.connect()

    async def _reset_connection(self) -> None:
        """Close and reset the broker connection state."""
        try:
            await nats_router.broker.stop()
        except IncorrectState:
            # Connection already reset; nothing else to do.
            return
