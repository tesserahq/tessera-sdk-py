"""
Identies Client - A Python client for the Identies API.

This package provides a convenient interface for interacting with the Vaulta API,
including client management and asset management functionality.
"""

from .client import IdentiesClient
from .exceptions import IdentiesError, IdentiesClientError, IdentiesServerError

# from .models import Client, ClientCreate, ClientUpdate, Asset, AssetUploadResponse
# from .utils import (
#     sign_serve_url,
# )

__version__ = "0.1.0"
__author__ = "Identies Team"

__all__ = [
    "IdentiesClient",
    "IdentiesError",
    "IdentiesClientError",
    "IdentiesServerError",
    # "Client",
    # "ClientCreate",
    # "ClientUpdate",
    # "Asset",
    # "AssetUploadResponse",
    # "sign_serve_url",
]
