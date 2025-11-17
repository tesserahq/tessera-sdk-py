import os
import logging
from typing import Optional, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.exceptions import HTTPException
from starlette import status
from starlette.responses import JSONResponse

from ..utils.auth import verify_token_dependency
from ..core.database_manager import DatabaseManager
from ..identies import IdentiesClient
from ..identies.exceptions import (
    IdentiesError,
    IdentiesAuthenticationError,
    IdentiesValidationError,
    IdentiesClientError,
    IdentiesServerError,
)

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        identies_base_url: Optional[str] = None,
        skip_paths: Optional[List[str]] = None,
        database_manager: Optional[DatabaseManager] = None,
    ):
        super().__init__(app)
        # Get Identies base URL from parameter or environment variable
        self.identies_base_url = identies_base_url or os.getenv("IDENTIES_BASE_URL")
        if not self.identies_base_url:
            raise ValueError(
                "Identies base URL must be provided either as parameter or IDENTIES_BASE_URL environment variable"
            )

        # Set default skip paths if none provided
        self.skip_paths = (
            skip_paths
            if skip_paths is not None
            else ["/health", "/openapi.json", "/docs"]
        )

        # Store database manager for creating sessions
        self.database_manager = database_manager

        # Initialize the Identies client
        self.identies_client = IdentiesClient(
            base_url=self.identies_base_url,
            timeout=10,  # Shorter timeout for middleware
            max_retries=1,  # Fewer retries for middleware
        )
        logger.info(
            f"AuthenticationMiddleware initialized with Identies base URL: {self.identies_base_url}"
        )

    async def _validate_api_key(
        self, request: Request, api_key: str, call_next
    ) -> JSONResponse:
        """
        Validate an X-API-Key using the Identies introspect endpoint.

        Args:
            request: The incoming request
            api_key: The API key to validate
            call_next: The next middleware/endpoint in the chain

        Returns:
            JSONResponse with appropriate status code and error message
        """
        try:
            logger.debug(f"Validating X-API-Key for request to {request.url.path}")

            # Set the API key in the client for this request
            self.identies_client.session.headers.update({"X-API-Key": api_key})

            # Call introspect to validate the API key
            introspect_response = self.identies_client.introspect()

            if introspect_response.active:
                logger.info(
                    f"X-API-Key validated successfully for user: {introspect_response.user_id}"
                )
                # Store user info in request state for use by endpoints
                request.state.user = introspect_response.user

                # Remove the X-API-Key from client headers after validation
                if "X-API-Key" in self.identies_client.session.headers:
                    del self.identies_client.session.headers["X-API-Key"]

                return await call_next(request)
            else:
                logger.warning("X-API-Key is not active (invalid, expired, or revoked)")
                return JSONResponse(
                    status_code=401, content={"error": "Invalid or inactive API key"}
                )

        except IdentiesAuthenticationError:
            logger.warning("X-API-Key authentication failed")
            return JSONResponse(status_code=401, content={"error": "Invalid API key"})
        except IdentiesValidationError as e:
            logger.warning(f"X-API-Key validation error: {e}")
            return JSONResponse(
                status_code=400,
                content={"error": f"API key validation error: {str(e)}"},
            )
        except (IdentiesClientError, IdentiesServerError) as e:
            logger.error(f"Identies client error during API key validation: {e}")
            return JSONResponse(
                status_code=503,
                content={"error": "Authentication service temporarily unavailable"},
            )
        except IdentiesError as e:
            logger.error(f"Unexpected Identies error during API key validation: {e}")
            return JSONResponse(
                status_code=500, content={"error": "Internal authentication error"}
            )
        except Exception as e:
            logger.error(f"Unexpected error during API key validation: {e}")
            return JSONResponse(
                status_code=500, content={"error": "Internal server error"}
            )
        finally:
            # Clean up: remove the X-API-Key from client headers if it's still there
            if "X-API-Key" in self.identies_client.session.headers:
                del self.identies_client.session.headers["X-API-Key"]

    async def dispatch(self, request: Request, call_next):
        # Check if the request path starts with any of the skip paths
        for skip_path in self.skip_paths:
            if request.url.path.startswith(skip_path):
                return await call_next(request)

        # Check for X-API-Key header first
        x_api_key = request.headers.get("X-API-Key")
        if x_api_key:
            return await self._validate_api_key(request, x_api_key, call_next)

        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401, content={"error": "Missing or invalid token"}
            )

        token = authorization[len("Bearer ") :]

        try:
            # Now manually pass the raw token with database manager
            verify_token_dependency(
                request, token, database_manager=self.database_manager
            )

            # Check if user was set after token verification
            if not hasattr(request.state, "user") or request.state.user is None:
                return JSONResponse(
                    status_code=401, content={"error": "User not found"}
                )

        except HTTPException as e:
            if e.status_code == status.HTTP_401_UNAUTHORIZED:
                return JSONResponse(status_code=401, content={"error": "Invalid token"})
            elif e.status_code == status.HTTP_403_FORBIDDEN:
                return JSONResponse(status_code=403, content={"error": "Forbidden"})

        return await call_next(request)
