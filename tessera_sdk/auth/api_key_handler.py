from tessera_sdk.identies import IdentiesClient
from tessera_sdk.config import get_settings
import logging

logger = logging.getLogger(__name__)


class APIKeyHandler:
    def __init__(self):
        self.settings = get_settings()
        self.identies_client = IdentiesClient(
            base_url=self.settings.identies_base_url,
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

        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            return False
        return True

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

        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            return ""
        return api_key.strip()

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

        # Set the API key in the client for this request
        self.identies_client.session.headers.update({"X-API-Key": api_key})

        # Call introspect to validate the API key
        introspect_response = self.identies_client.introspect()

        if introspect_response.active:
            logger.info(
                f"X-API-Key validated successfully for user: {introspect_response.user_id}"
            )

            # Remove the X-API-Key from client headers after validation
            if "X-API-Key" in self.identies_client.session.headers:
                del self.identies_client.session.headers["X-API-Key"]

            return introspect_response.user
        else:
            return False
