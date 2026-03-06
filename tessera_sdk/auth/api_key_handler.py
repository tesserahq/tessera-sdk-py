from typing import Optional

import logging

from tessera_sdk.config import get_settings
from tessera_sdk.identies import IdentiesClient

logger = logging.getLogger(__name__)


def _is_api_key(token: str) -> bool:
    """Return True if the token looks like an API key (ak_<key_id>.<secret>)."""
    return bool(token and token.startswith("ak_") and "." in token)


def _get_bearer_token(headers) -> str | None:
    """Extract Bearer token from Authorization header. Supports Mapping or Dict."""
    auth = None
    if hasattr(headers, "get"):
        auth = headers.get("authorization") or headers.get("Authorization")
    else:
        if "authorization" in headers:
            auth = headers["authorization"]
        elif "Authorization" in headers:
            auth = headers["Authorization"]
        else:
            auth = None
    if not auth or not isinstance(auth, str):
        return None
    auth = auth.strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


class APIKeyHandler:
    def __init__(self):
        self.settings = get_settings()
        self.identies_client = IdentiesClient(
            base_url=self.settings.identies_api_url,
            timeout=int(self.settings.tesserasdk_auth_middleware_timeout),
        )

    def has_api_key_header(self, headers) -> bool:
        """
        Check if the request has a valid X-API-Key header. Supports Mapping or Dict.
        """
        api_key = None
        if hasattr(headers, "get"):
            api_key = headers.get("x-api-key")
            if not api_key:
                api_key = headers.get("X-API-Key")
        else:
            if "x-api-key" in headers:
                api_key = headers["x-api-key"]
            elif "X-API-Key" in headers:
                api_key = headers["X-API-Key"]
            else:
                api_key = None

        if api_key and isinstance(api_key, str) and api_key.strip():
            return True

        bearer = _get_bearer_token(headers)
        if bearer and _is_api_key(bearer):
            return True
        return False

    def get_api_key(self, headers) -> str:
        """
        Get the API key from the request headers (supports Mapping or Dict).
        Accepts both "X-API-Key" and "x-api-key" header keys,
        case-insensitive in practice.
        """
        api_key = None
        if hasattr(headers, "get"):
            api_key = headers.get("x-api-key")
            if not api_key:
                api_key = headers.get("X-API-Key")
        else:
            if "x-api-key" in headers:
                api_key = headers["x-api-key"]
            elif "X-API-Key" in headers:
                api_key = headers["X-API-Key"]
            else:
                api_key = ""

        if api_key and isinstance(api_key, str) and api_key.strip():
            return api_key.strip()

        bearer = _get_bearer_token(headers)
        if bearer and _is_api_key(bearer):
            return bearer
        return ""

    def validate(self, api_key: str):
        """
        Validate an X-API-Key using the Identies introspect endpoint.

        Args:
            request: The incoming request
            api_key: The API key to validate

        Returns:
            True if the API key is valid, False otherwise
        """
        if not api_key:
            return False

        # Set the API key as Bearer; Identies introspect accepts JWT or API key in Bearer
        self.identies_client.session.headers.update(
            {"Authorization": f"Bearer {api_key}"}
        )

        # Call introspect to validate the API key
        introspect_response = self.identies_client.introspect()

        if introspect_response.active:
            logger.info(
                f"X-API-Key validated successfully for user: {introspect_response.user_id}"
            )

            # Remove the Bearer header after validation
            if "Authorization" in self.identies_client.session.headers:
                del self.identies_client.session.headers["Authorization"]

            return introspect_response.user
        else:
            return False
