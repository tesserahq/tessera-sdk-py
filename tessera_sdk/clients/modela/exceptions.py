from .._base.exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)


class ModelaError(TesseraError):
    pass


class ModelaClientError(TesseraClientError):
    pass


class ModelaServerError(TesseraServerError):
    pass


class ModelaAuthenticationError(TesseraAuthenticationError):
    pass


class ModelaNotFoundError(TesseraNotFoundError):
    pass


class ModelaValidationError(TesseraValidationError):
    pass
