import inspect
import logging
from typing import Any, Awaitable, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from ...clients._base.exceptions import (
    TesseraAuthenticationError,
    TesseraClientError,
    TesseraError,
    TesseraServerError,
    TesseraValidationError,
)
from ...clients.custos import CustosClient
from ...config import get_settings
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


DomainResolver = Callable[[Request], "str | Awaitable[str]"]


def authorize(
    action: str,
    resource: str,
    domain_resolver: Optional[DomainResolver] = None,
    *,
    domain_dependency: Optional[Callable[..., Any]] = None,
):
    """
    Factory function that creates a FastAPI dependency for authorization.

    Pass exactly one of:

    - ``domain_dependency``: a FastAPI dependency that returns the domain
      string. It is resolved like any other dependency, so it can declare the
      request session and reuse entities the route already loads (FastAPI
      caches each dependency per request). Prefer a plain ``def``: FastAPI runs
      it in the threadpool. It is resolved before the authenticated-user check;
      the authentication middleware has already rejected anonymous requests.
    - ``domain_resolver``: a callable taking the ``Request``. A coroutine
      function is awaited; a plain function runs in the threadpool. A resolver
      that touches the database must be a plain function.

    Args:
        action: The action to authorize (e.g., 'create', 'read', 'update', 'delete')
        resource: The resource type to authorize (e.g., 'account', 'vehicle')
        domain_resolver: Callable that takes a Request and returns the domain
        domain_dependency: FastAPI dependency that returns the domain

    Returns:
        A FastAPI dependency function that performs authorization
    """
    if (domain_resolver is None) == (domain_dependency is None):
        raise ValueError(
            "authorize() needs exactly one of domain_resolver or domain_dependency"
        )

    if domain_dependency is not None:

        async def authorization_dependency_with_domain(
            request: Request, domain: str = Depends(domain_dependency)
        ):
            user_id = _require_user_id(request)
            return await run_in_threadpool(
                _check_authorization, request, user_id, action, resource, domain
            )

        return authorization_dependency_with_domain

    async def authorization_dependency(request: Request):
        user_id = _require_user_id(request)

        # Resolve domain using the provided resolver
        if inspect.iscoroutinefunction(domain_resolver):
            domain = await domain_resolver(request)
        else:
            domain = await run_in_threadpool(domain_resolver, request)
            # A plain callable may still return an awaitable (e.g. a lambda
            # around a coroutine function).
            if inspect.isawaitable(domain):
                domain = await domain

        return await run_in_threadpool(
            _check_authorization, request, user_id, action, resource, domain
        )

    return authorization_dependency


def _require_user_id(request: Request) -> str:
    # Get user from request state (set by authentication middleware)
    if not hasattr(request.state, "user") or request.state.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated",
        )

    user = request.state.user

    # Extract user_id from user object
    if hasattr(user, "id") and user.id is not None:
        return str(user.id)
    if hasattr(user, "user_id") and user.user_id is not None:
        return str(user.user_id)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User ID not found",
    )


def _check_authorization(
    request: Request, user_id: str, action: str, resource: str, domain: str
) -> bool:
    """Cache lookup and Custos check. Blocking: callers run it in the threadpool."""
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
            if not cached_result.get("allowed", False):
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
