from collections.abc import Iterable

from ...infra.events import Event
from .._base.exceptions import (
    TesseraAuthenticationError,
    TesseraClientError,
    TesseraError,
    TesseraNotFoundError,
    TesseraServerError,
    TesseraValidationError,
)


class _CompletionEvents:
    events: tuple[Event, ...]

    def _set_events(self, events: tuple[Event, ...]) -> None:
        self.events = events


class ModelaError(_CompletionEvents, TesseraError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        *,
        events: Iterable[Event] = (),
    ):
        super().__init__(message, status_code)
        self._set_events(tuple(events))


class ModelaClientError(_CompletionEvents, TesseraClientError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        *,
        events: Iterable[Event] = (),
    ):
        super().__init__(message, status_code)
        self._set_events(tuple(events))


class ModelaServerError(_CompletionEvents, TesseraServerError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        *,
        events: Iterable[Event] = (),
    ):
        super().__init__(message, status_code)
        self._set_events(tuple(events))


class ModelaAuthenticationError(_CompletionEvents, TesseraAuthenticationError):
    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        events: Iterable[Event] = (),
    ):
        super().__init__(message)
        self._set_events(tuple(events))


class ModelaNotFoundError(_CompletionEvents, TesseraNotFoundError):
    def __init__(
        self,
        message: str = "Resource not found",
        *,
        events: Iterable[Event] = (),
    ):
        super().__init__(message)
        self._set_events(tuple(events))


class ModelaValidationError(_CompletionEvents, TesseraValidationError):
    def __init__(
        self,
        message: str = "Validation error",
        *,
        events: Iterable[Event] = (),
    ):
        super().__init__(message)
        self._set_events(tuple(events))
