from starlette.requests import Request

from tessera_sdk.auth.api_key_handler import APIKeyHandler
from tessera_sdk.auth.token_handler import TokenHandler


class AuthHandler:
    """Handles both API key and Bearer token validation."""

    def __init__(self, user_service_factory=None):
        self.api_key_handler = APIKeyHandler()
        self.token_handler = TokenHandler()

    def validate(self, request: Request) -> bool:
        """
        Validate the request using either API key or Bearer token.
        Tries API key first; if not present or invalid, tries Bearer token.
        Sets request.state.user on success.

        Returns:
            True if validation succeeds, False otherwise.
        """
        # Try API key first
        if self.api_key_handler.has_api_key_header(request):
            api_key = self.api_key_handler.get_api_key(request)
            if self.api_key_handler.validate(request, api_key):
                return True

        # Try Bearer token
        if self.token_handler.has_bearer_token_header(request):
            token = self.token_handler.get_bearer_token(request)
            if self.token_handler.verify(token):
                return True

        return False
