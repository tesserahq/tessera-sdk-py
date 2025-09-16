"""
Quore Client - A Python client for the Quore API.

This package provides a convenient interface for interacting with the Quore API,
including text summarization and other NLP functionality.
"""

from .client import QuoreClient
from .exceptions import (
    QuoreError,
    QuoreClientError,
    QuoreServerError,
    QuoreAuthenticationError,
    QuoreNotFoundError,
    QuoreValidationError,
)
from .schemas import SummarizeRequest, SummarizeResponse

__version__ = "0.1.0"
__author__ = "Quore Team"

__all__ = [
    "QuoreClient",
    "QuoreError",
    "QuoreClientError",
    "QuoreServerError",
    "QuoreAuthenticationError",
    "QuoreNotFoundError",
    "QuoreValidationError",
    "SummarizeRequest",
    "SummarizeResponse",
]
