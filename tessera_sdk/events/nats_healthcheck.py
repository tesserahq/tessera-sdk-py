"""
FastStream NATS healthcheck for validating NATS connectivity and message delivery.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Optional

from nats.aio.client import Client as NatsClient  # type: ignore[import]
from faststream.exceptions import IncorrectState  # type: ignore[import]

from tessera_sdk.config import get_settings
from tessera_sdk.events.nats_router import nats_router

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthcheckStep:
    """Represents a single step in the healthcheck process."""

    def __init__(self, name: str, status: str, error: Optional[str] = None):
        self.name = name
        self.status = status  # "success" or "failed"
        self.error = error

    def to_dict(self) -> dict[str, str | None]:
        """Convert step to dictionary format."""
        result: dict[str, str | None] = {
            "step": self.name,
            "status": self.status,
        }
        if self.error:
            result["error"] = self.error
        return result


class NatsHealthcheck:
    """Perform health checks on NATS by connecting, publishing, and validating message receipt."""

    def __init__(self, timeout: float = 5.0):
        """
        Initialize the NATS healthcheck.

        Args:
            timeout: Maximum time to wait for message receipt in seconds (default: 5.0)
        """
        self._enabled = settings.nats_enabled
        self._logger = logger
        self._timeout = timeout
        if not self._enabled:
            self._logger.warning("NATS healthcheck is DISABLED by configuration")

    async def check(self) -> dict[str, Any]:
        """
        Perform a health check by connecting, sending a test message, and validating receipt.

        Returns:
            A dictionary with the following structure:
            - "status" (bool): True if the health check passes, False otherwise
            - "error" (str, optional): Overall error message describing what went wrong (only present when status is False)
            - "settings" (dict): NATS-related configuration settings:
                - "nats_enabled" (bool): Whether NATS is enabled
                - "nats_url" (str): NATS server URL
                - "timeout" (float): Healthcheck timeout in seconds
            - "steps" (list): List of step dictionaries, each with:
                - "step" (str): Name of the step
                - "status" (str): "success" or "failed"
                - "error" (str, optional): Error message for failed steps
        """
        steps: list[HealthcheckStep] = []

        # Collect NATS settings
        settings_info = {
            "nats_enabled": self._enabled,
            "nats_url": settings.nats_url,
            "timeout": self._timeout,
        }

        # Step 0: Check if NATS is enabled
        if not self._enabled:
            error_msg = "NATS healthcheck skipped - NATS is disabled"
            self._logger.warning(error_msg)
            steps.append(HealthcheckStep("Check NATS enabled", "failed", error_msg))
            return {
                "status": False,
                "error": error_msg,
                "settings": settings_info,
                "steps": [step.to_dict() for step in steps],
            }
        steps.append(HealthcheckStep("Check NATS enabled", "success"))

        test_subject = f"_healthcheck.{uuid.uuid4().hex}"
        test_message_id = str(uuid.uuid4())
        nats_client: Optional[NatsClient] = None
        subscription = None

        try:
            # Step 1: Ensure connection is ready for the broker (to reuse existing connection if available)
            try:
                await self._ensure_connection_ready()
                steps.append(
                    HealthcheckStep("Ensure broker connection ready", "success")
                )
            except Exception as e:
                error_msg = f"Failed to ensure broker connection ready: {type(e).__name__}: {str(e)}"
                steps.append(
                    HealthcheckStep(
                        "Ensure broker connection ready", "failed", error_msg
                    )
                )
                raise

            # Step 2: Create a temporary NATS client for subscription
            # This allows us to subscribe and receive messages independently
            try:
                self._logger.debug("Creating temporary NATS client for healthcheck")
                nats_client = NatsClient()
                steps.append(HealthcheckStep("Create temporary NATS client", "success"))
            except Exception as e:
                error_msg = (
                    f"Failed to create NATS client: {type(e).__name__}: {str(e)}"
                )
                steps.append(
                    HealthcheckStep("Create temporary NATS client", "failed", error_msg)
                )
                raise

            # Step 3: Connect temporary NATS client
            try:
                await nats_client.connect(
                    servers=[settings.nats_url], connect_timeout=int(self._timeout)
                )
                steps.append(
                    HealthcheckStep("Connect temporary NATS client", "success")
                )
            except Exception as e:
                error_msg = f"Failed to connect to NATS server ({settings.nats_url}): {type(e).__name__}: {str(e)}"
                steps.append(
                    HealthcheckStep(
                        "Connect temporary NATS client", "failed", error_msg
                    )
                )
                raise

            # Step 4: Subscribe to the test subject
            try:
                self._logger.debug(
                    f"Subscribing to healthcheck subject: {test_subject}"
                )
                subscription = await nats_client.subscribe(test_subject)
                steps.append(
                    HealthcheckStep(
                        f"Subscribe to test subject ({test_subject})", "success"
                    )
                )
            except Exception as e:
                error_msg = (
                    f"Failed to subscribe to test subject: {type(e).__name__}: {str(e)}"
                )
                steps.append(
                    HealthcheckStep(
                        f"Subscribe to test subject ({test_subject})",
                        "failed",
                        error_msg,
                    )
                )
                raise

            try:
                # Step 5: Publish test message using the broker
                try:
                    test_message = {
                        "healthcheck_id": test_message_id,
                        "timestamp": asyncio.get_event_loop().time(),
                    }
                    self._logger.debug(
                        f"Publishing healthcheck message: {test_message_id} to {test_subject}"
                    )
                    await nats_router.broker.publish(test_message, subject=test_subject)
                    steps.append(HealthcheckStep("Publish test message", "success"))
                except Exception as e:
                    error_msg = (
                        f"Failed to publish test message: {type(e).__name__}: {str(e)}"
                    )
                    steps.append(
                        HealthcheckStep("Publish test message", "failed", error_msg)
                    )
                    raise

                # Step 6: Wait for message to be received (with timeout)
                try:
                    msg = await asyncio.wait_for(
                        subscription.next_msg(), timeout=self._timeout
                    )
                    steps.append(HealthcheckStep("Receive test message", "success"))
                except asyncio.TimeoutError:
                    error_msg = (
                        f"Message {test_message_id} not received within {self._timeout}s. "
                        f"This may indicate a connectivity issue, message routing problem, or NATS server overload."
                    )
                    steps.append(
                        HealthcheckStep("Receive test message", "failed", error_msg)
                    )
                    overall_error = (
                        f"Healthcheck failed: message {test_message_id} not received within {self._timeout}s. "
                        f"This may indicate a connectivity issue, message routing problem, or NATS server overload."
                    )
                    self._logger.warning(overall_error)
                    return {
                        "status": False,
                        "error": overall_error,
                        "settings": settings_info,
                        "steps": [step.to_dict() for step in steps],
                    }

                # Step 7: Parse the received message
                try:
                    received_message = json.loads(msg.data.decode())
                    self._logger.debug(
                        f"Received healthcheck message: {received_message}"
                    )
                    steps.append(HealthcheckStep("Parse received message", "success"))
                except Exception as e:
                    error_msg = f"Failed to parse received message: {type(e).__name__}: {str(e)}"
                    steps.append(
                        HealthcheckStep("Parse received message", "failed", error_msg)
                    )
                    overall_error = f"Healthcheck failed: {error_msg}"
                    self._logger.warning(overall_error)
                    return {
                        "status": False,
                        "error": overall_error,
                        "settings": settings_info,
                        "steps": [step.to_dict() for step in steps],
                    }

                # Step 8: Validate message structure
                if not isinstance(received_message, dict):
                    error_msg = (
                        f"Received message is not a dict: {type(received_message)}"
                    )
                    steps.append(
                        HealthcheckStep(
                            "Validate message structure", "failed", error_msg
                        )
                    )
                    overall_error = f"Healthcheck failed: {error_msg}"
                    self._logger.warning(overall_error)
                    return {
                        "status": False,
                        "error": overall_error,
                        "settings": settings_info,
                        "steps": [step.to_dict() for step in steps],
                    }
                steps.append(HealthcheckStep("Validate message structure", "success"))

                # Step 9: Validate message ID match
                if received_message.get("healthcheck_id") != test_message_id:
                    error_msg = (
                        f"Message ID mismatch. Expected {test_message_id}, "
                        f"got {received_message.get('healthcheck_id')}"
                    )
                    steps.append(
                        HealthcheckStep("Validate message ID", "failed", error_msg)
                    )
                    overall_error = f"Healthcheck failed: {error_msg}"
                    self._logger.warning(overall_error)
                    return {
                        "status": False,
                        "error": overall_error,
                        "settings": settings_info,
                        "steps": [step.to_dict() for step in steps],
                    }
                steps.append(HealthcheckStep("Validate message ID", "success"))

                self._logger.info(
                    f"Healthcheck passed: message {test_message_id} received and validated"
                )
                return {
                    "status": True,
                    "settings": settings_info,
                    "steps": [step.to_dict() for step in steps],
                }

            finally:
                # Clean up subscription
                if subscription is not None:
                    try:
                        await subscription.unsubscribe()
                    except Exception as e:
                        self._logger.warning(
                            f"Failed to unsubscribe from {test_subject}: {e}"
                        )

        except IncorrectState:
            error_msg = (
                "NATS connection in IncorrectState. "
                "The broker connection is not in a valid state for publishing messages."
            )
            # Add the failed step if we don't already have an error for this step
            if not any(
                step.name == "Ensure broker connection ready"
                and step.status == "failed"
                for step in steps
            ):
                steps.append(
                    HealthcheckStep(
                        "Ensure broker connection ready", "failed", error_msg
                    )
                )
            self._logger.warning(f"Healthcheck failed: {error_msg}")
            try:
                await self._reset_connection()
            except Exception as reset_error:
                self._logger.warning(
                    f"Failed to reset connection during healthcheck: {reset_error}"
                )
                error_msg += f" Additionally, connection reset failed: {reset_error}"
            overall_error = f"Healthcheck failed: {error_msg}"
            return {
                "status": False,
                "error": overall_error,
                "settings": settings_info,
                "steps": [step.to_dict() for step in steps],
            }
        except asyncio.TimeoutError:
            error_msg = (
                f"Connection timeout after {self._timeout}s. "
                f"This may indicate the NATS server is unreachable or not responding."
            )
            # The timeout step should already be added in the try block, but add here if needed
            if not any(
                step.name == "Connect temporary NATS client" and step.status == "failed"
                for step in steps
            ):
                steps.append(
                    HealthcheckStep(
                        "Connect temporary NATS client", "failed", error_msg
                    )
                )
            overall_error = f"Healthcheck failed: {error_msg}"
            self._logger.warning(overall_error)
            return {
                "status": False,
                "error": overall_error,
                "settings": settings_info,
                "steps": [step.to_dict() for step in steps],
            }
        except Exception as e:
            error_msg = f"Unexpected exception: {type(e).__name__}: {str(e)}"
            # Only add step if we haven't already tracked this failure in a specific step
            if not steps or steps[-1].status == "success":
                steps.append(HealthcheckStep("Unexpected error", "failed", error_msg))
            overall_error = f"Healthcheck failed with {error_msg}"
            self._logger.exception(overall_error)
            return {
                "status": False,
                "error": overall_error,
                "settings": settings_info,
                "steps": [step.to_dict() for step in steps],
            }
        finally:
            # Clean up the temporary NATS client
            if nats_client is not None:
                try:
                    await nats_client.close()
                except Exception as e:
                    self._logger.warning(f"Failed to close temporary NATS client: {e}")

    async def _ensure_connection_ready(self) -> None:
        """Ensure the broker connection is ready before healthcheck."""
        try:
            self._logger.debug("Ensuring NATS connection is ready for healthcheck")
            await nats_router.broker.connect()
            self._logger.debug("NATS connection ready for healthcheck")
        except IncorrectState:
            self._logger.warning(
                "NATS connection in IncorrectState during healthcheck; resetting"
            )
            await self._reset_connection()
            await nats_router.broker.connect()
        except Exception:
            self._logger.exception("NATS connect failed during healthcheck")
            raise

    async def _reset_connection(self) -> None:
        """Close and reset the broker connection state."""
        try:
            self._logger.warning("Resetting NATS connection during healthcheck")
            await nats_router.broker.stop()
        except IncorrectState:
            # Connection already reset; nothing else to do.
            return
        except Exception:
            self._logger.exception("NATS reset failed during healthcheck")
            raise
