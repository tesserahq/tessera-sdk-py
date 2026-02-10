import logging
from typing import Optional, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.exceptions import HTTPException
from starlette import status
from starlette.responses import JSONResponse

from ..auth.api_key_handler import APIKeyHandler
from ..auth.token_handler import TokenHandler
from ..schemas.user import UserNeedsOnboarding

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        skip_paths: Optional[List[str]] = None,
        user_service_factory=None,
    ):
        super().__init__(app)
        self.user_service_factory = user_service_factory
        self.api_key_handler = APIKeyHandler()
        self.token_handler = TokenHandler()
        self.skip_paths = (
            skip_paths
            if skip_paths is not None
            else ["/health", "/openapi.json", "/docs"]
        )

    async def dispatch(self, request: Request, call_next):
        # Check if the request path starts with any of the skip paths
        for skip_path in self.skip_paths:
            if request.url.path.startswith(skip_path):
                return await call_next(request)

        # Check for X-API-Key header first
        if self.api_key_handler.has_api_key_header(request.headers):
            api_key = self.api_key_handler.get_api_key(request.headers)

            user = self.api_key_handler.validate(api_key)
            if not user:
                return JSONResponse(
                    status_code=401, content={"error": "Invalid API key"}
                )

            # Store user info in request state for use by endpoints
            request.state.user = user

            return await call_next(request)

        # Check for Bearer token (may be JWT or API key if it starts with "ak_")
        if not self.token_handler.has_bearer_token_header(request.headers):
            return JSONResponse(
                status_code=401, content={"error": "Missing or invalid token"}
            )

        token = self.token_handler.get_bearer_token(request.headers)

        # Bearer token starting with "ak_" is treated as an API key
        if token.startswith("ak_"):
            user = self.api_key_handler.validate(token)
            if not user:
                return JSONResponse(
                    status_code=401, content={"error": "Invalid API key"}
                )

            request.state.user = user
            return await call_next(request)

        # Otherwise treat as JWT
        try:
            payload = self.token_handler.verify(token)

            # Extract user ID from JWT payload
            external_user_id = payload["sub"]

            user_service = self.user_service_factory()

            try:
                # User not in cache or cache was invalid, check database
                user = user_service.get_user_by_id_or_external_id(external_user_id)
            finally:
                if hasattr(user_service, "db"):
                    user_service.db.close()
                elif callable(getattr(user_service, "close", None)):
                    user_service.close()

            if not user:
                user = UserNeedsOnboarding(
                    external_id=external_user_id,
                    needs_onboarding=True,
                )

            request.state.user = user

        except HTTPException as e:
            if e.status_code == status.HTTP_401_UNAUTHORIZED:
                return JSONResponse(status_code=401, content={"error": "Invalid token"})
            elif e.status_code == status.HTTP_403_FORBIDDEN:
                return JSONResponse(status_code=403, content={"error": "Forbidden"})

        return await call_next(request)
