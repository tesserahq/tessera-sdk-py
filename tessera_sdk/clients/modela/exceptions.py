from collections.abc import Iterable
from typing import ClassVar

from ...infra.events import Event
from ...mcp import TruncationMarker
from .._base.exceptions import (
    TesseraAuthenticationError,
    TesseraClientError,
    TesseraError,
    TesseraNotFoundError,
    TesseraServerError,
    TesseraValidationError,
)


class ModelaError(TesseraError):
    """Base class for every Modela client error.

    ``events`` holds committed domain events Modela returned in the error body,
    so a caller can reconcile state with a single ``except ModelaError``.
    ``truncations`` holds the ``events`` channel marker, if that list is partial.
    """

    events: tuple[Event, ...]
    truncations: tuple[TruncationMarker, ...]

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        *,
        events: Iterable[Event] = (),
        truncations: Iterable[TruncationMarker] = (),
    ):
        super().__init__(message, status_code)
        self.events = tuple(events)
        self.truncations = tuple(truncations)


class ModelaClientError(ModelaError, TesseraClientError):
    pass


class ModelaServerError(ModelaError, TesseraServerError):
    pass


class ModelaAuthenticationError(ModelaError, TesseraAuthenticationError):
    def __init__(
        self,
        message: str = "Authentication failed",
        status_code: int = 401,
        *,
        events: Iterable[Event] = (),
        truncations: Iterable[TruncationMarker] = (),
    ):
        super().__init__(message, status_code, events=events, truncations=truncations)


class ModelaNotFoundError(ModelaError, TesseraNotFoundError):
    def __init__(
        self,
        message: str = "Resource not found",
        status_code: int = 404,
        *,
        events: Iterable[Event] = (),
        truncations: Iterable[TruncationMarker] = (),
    ):
        super().__init__(message, status_code, events=events, truncations=truncations)


class ModelaValidationError(ModelaError, TesseraValidationError):
    def __init__(
        self,
        message: str = "Validation error",
        status_code: int = 400,
        *,
        events: Iterable[Event] = (),
        truncations: Iterable[TruncationMarker] = (),
    ):
        super().__init__(message, status_code, events=events, truncations=truncations)


class _ModelaErrorFactory:
    """Construct Modela exceptions from HTTP failures in one place.

    Both the synchronous and streaming transports delegate to this factory so
    status classification, messages, and committed-event handling cannot drift.
    Adding a special status only requires extending ``_EXACT_STATUS_TYPES``.
    """

    _EXACT_STATUS_TYPES: ClassVar[dict[int, tuple[type[TesseraError], str]]] = {
        400: (ModelaValidationError, "Bad request"),
        401: (ModelaAuthenticationError, "Authentication failed"),
        404: (ModelaNotFoundError, "Resource not found"),
    }
    _BASE_ERROR_TYPES: ClassVar[dict[type[TesseraError], type[TesseraError]]] = {
        TesseraAuthenticationError: ModelaAuthenticationError,
        TesseraClientError: ModelaClientError,
        TesseraError: ModelaError,
        TesseraNotFoundError: ModelaNotFoundError,
        TesseraServerError: ModelaServerError,
        TesseraValidationError: ModelaValidationError,
    }

    @classmethod
    def from_http_status(
        cls,
        status_code: int,
        context: str,
        detail: str | None,
        events: Iterable[Event] = (),
        truncations: Iterable[TruncationMarker] = (),
    ) -> TesseraError:
        error_type, default_detail = cls._classification_for(status_code)
        message = cls._message(
            error_type,
            status_code,
            context,
            detail or default_detail,
        )
        return cls._construct(error_type, message, status_code, events, truncations)

    @classmethod
    def from_tessera_error(
        cls,
        error: TesseraError,
        events: Iterable[Event] = (),
        truncations: Iterable[TruncationMarker] = (),
    ) -> TesseraError:
        error_type = cls._BASE_ERROR_TYPES.get(type(error), ModelaError)
        return cls._construct(
            error_type, str(error), error.status_code, events, truncations
        )

    @classmethod
    def _classification_for(cls, status_code: int):
        exact = cls._EXACT_STATUS_TYPES.get(status_code)
        if exact is not None:
            return exact
        if 400 <= status_code < 500:
            return ModelaClientError, "Client error"
        if 500 <= status_code < 600:
            return ModelaServerError, "Server error"
        return ModelaError, "Unexpected response"

    @staticmethod
    def _message(error_type, status_code: int, context: str, detail: str) -> str:
        if error_type in (
            ModelaAuthenticationError,
            ModelaNotFoundError,
            ModelaValidationError,
        ):
            return f"{context}: {detail}"
        return f"{context}: {status_code} {detail}"

    @staticmethod
    def _construct(error_type, message, status_code, events, truncations):
        return error_type(
            message,
            status_code,
            events=events,
            truncations=truncations,
        )
