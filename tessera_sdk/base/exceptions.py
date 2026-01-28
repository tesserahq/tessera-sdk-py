from fastapi import HTTPException, status

"""
Base exceptions for the Tessera SDK.
"""


class TesseraError(Exception):
    """Base exception for all Tessera-related errors."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class TesseraClientError(TesseraError):
    """Exception raised for client-side errors (4xx status codes)."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, status_code)


class TesseraServerError(TesseraError):
    """Exception raised for server-side errors (5xx status codes)."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, status_code)


class TesseraAuthenticationError(TesseraError):
    """Exception raised for authentication errors (401 status code)."""

    def __init__(self, message: str = "Authentication failed", status_code: int = 401):
        super().__init__(message, status_code)


class TesseraNotFoundError(TesseraError):
    """Exception raised when a resource is not found (404 status code)."""

    def __init__(self, message: str = "Resource not found", status_code: int = 404):
        super().__init__(message, status_code)


class TesseraValidationError(TesseraError):
    """Exception raised for validation errors (400 status code)."""

    def __init__(self, message: str = "Validation error", status_code: int = 400):
        super().__init__(message, status_code)


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str, **kwargs):
        """Returns HTTP 403"""
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthenticatedException(HTTPException):
    def __init__(self):
        """Returns HTTP 401"""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication"
        )
