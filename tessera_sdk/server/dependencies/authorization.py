import logging
from typing import Callable, Awaitable, Optional
from fastapi import Request, HTTPException, status

from ...config import get_settings
from ...clients._base.exceptions import (
    TesseraAuthenticationError,
    TesseraValidationError,
    TesseraClientError,
    TesseraServerError,
    TesseraError,
)
from ...clients.custos import CustosClient
from ...infra.cache import Cache

logger = logging.getLogger(__name__)

# Module-level cache instance (lazy-loaded)
_authorization_cache: Optional[Cache] = None


def _get_authorization_cache() -> Optional[Cache]:
    """
    Get or create the authorization cache instance.

    The cache is only created if authorization_cache_enabled is True in config.
    This allows enabling/disabling the cache via environment variables.
    """
    global _authorization_cache

    # Always check the config setting to respect runtime changes
    settings = get_settings()
    if not settings.authorization_cache_enabled:
        return None

    # Only create cache if enabled and not already created
    if _authorization_cache is None:
        try:
            _authorization_cache = Cache(namespace="authorization")
            logger.debug("Authorization cache initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize authorization cache: {e}")
            return None

    return _authorization_cache


def _extract_auth_token(request: Request) -> str:
    """
    Extract and clean the authentication token from the Authorization header.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    # Remove "Bearer " prefix if present
    if authorization.startswith("Bearer "):
        return authorization[len("Bearer ") :]

    return authorization


def authorize(
    action: str,
    resource: str,
    domain_resolver: Callable[[Request], Awaitable[str]],
):
    """
    Factory function that creates a FastAPI dependency for authorization.

    Args:
        action: The action to authorize (e.g., 'create', 'read', 'update', 'delete')
        resource: The resource type to authorize (e.g., 'account', 'vehicle')
        domain_resolver: Async function that takes a Request and returns the domain string

    Returns:
        A FastAPI dependency function that performs authorization
    """

    async def authorization_dependency(request: Request):
        # Get user from request state (set by authentication middleware)
        if not hasattr(request.state, "user") or request.state.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated",
            )

        user = request.state.user

        # Extract user_id from user object
        if hasattr(user, "id") and user.id is not None:
            user_id = str(user.id)
        elif hasattr(user, "user_id") and user.user_id is not None:
            user_id = str(user.user_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found",
            )

        # Resolve domain using the provided resolver
        domain = await domain_resolver(request)

        # Get settings
        settings = get_settings()
        custos_api_url = settings.custos_api_url
        if not custos_api_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Custos service not configured",
            )

        # Generate cache key
        cache_key = f"{user_id}:{action}:{resource}:{domain}"

        # Check cache if enabled
        cache = _get_authorization_cache()
        if cache:
            cached_result = cache.read(cache_key)
            if cached_result is not None:
                logger.debug(f"Authorization cache hit for key: {cache_key}")
                if not cached_result.get("authorized", False):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied",
                    )
                return True

        # Extract authentication token from request headers
        auth_token = _extract_auth_token(request)

        # Create Custos client with authentication token
        custos_client = CustosClient(base_url=custos_api_url, api_token=auth_token)

        try:
            # Call Custos authorization endpoint
            response = custos_client.authorize(
                user_id=user_id,
                action=action,
                resource=resource,
                domain=domain,
            )

            # Check if authorization was granted
            if not response.allowed:
                if cache:
                    cache.write(
                        cache_key,
                        {"allowed": False},
                        ttl=settings.authorization_cache_ttl,
                    )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )

            if cache:
                cache.write(
                    cache_key,
                    {"allowed": True},
                    ttl=settings.authorization_cache_ttl,
                )

        except TesseraAuthenticationError as e:
            logger.warning(f"Custos authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
            )
        except TesseraValidationError as e:
            logger.warning(f"Custos validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error: {str(e)}",
            )
        except (TesseraClientError, TesseraServerError) as e:
            logger.error(f"Custos service error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authorization service unavailable",
            )
        except TesseraError as e:
            logger.error(f"Custos error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization check failed",
            )
        finally:
            # Clean up: remove Authorization header from client session
            if "Authorization" in custos_client.session.headers:
                del custos_client.session.headers["Authorization"]

        return True

    return authorization_dependency
