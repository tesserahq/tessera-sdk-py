import logging
from typing import Callable, Awaitable, Optional
from fastapi import Request, HTTPException, status

from ..config import get_settings
from ..custos import CustosClient
from ..custos.exceptions import (
    CustosError,
    CustosClientError,
    CustosServerError,
    CustosAuthenticationError,
    CustosValidationError,
)
from ..utils.cache import Cache

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

    Args:
        request: The FastAPI request object

    Returns:
        The authentication token without the "Bearer " prefix

    Raises:
        HTTPException: 401 if Authorization header is missing or invalid
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

    Example:
        >>> async def infer_domain(request: Request) -> str:
        ...     account_id = request.path_params.get("account_id")
        ...     if account_id:
        ...         return f"account:{account_id}"
        ...     raise HTTPException(status_code=400, detail="Cannot infer domain")
        ...
        >>> authorize_vehicle_create = authorize(
        ...     action="create",
        ...     resource="vehicle",
        ...     domain_resolver=infer_domain
        ... )
    """

    async def authorization_dependency(request: Request):
        """
        FastAPI dependency that performs authorization check.

        Raises:
            HTTPException: 401 if authentication token is missing
            HTTPException: 403 if authorization is denied
            HTTPException: 400 if domain cannot be inferred

        Example:
            First, create a domain resolver function::

                async def infer_domain(request: Request) -> str:
                    # Extract account_id from path parameters
                    if "account_id" in request.path_params:
                        return f"account:{request.path_params['account_id']}"

                    # Or load from database if needed
                    if "vehicle_id" in request.path_params:
                        vehicle_id = request.path_params["vehicle_id"]
                        vehicle = await get_vehicle(vehicle_id)
                        return f"account:{vehicle.account_id}"

                    raise HTTPException(
                        status_code=400,
                        detail="Cannot infer domain"
                    )

            Then create authorization dependencies::

                from fastapi import Depends
                from tessera_sdk.utils.authorization_dependency import authorize

                authorize_vehicle_create = authorize(
                    action="create",
                    resource="vehicle",
                    domain_resolver=infer_domain,
                )

                authorize_vehicle_update = authorize(
                    action="update",
                    resource="vehicle",
                    domain_resolver=infer_domain,
                )

            Use in routes::

                @app.post("/accounts/{account_id}/vehicles")
                async def create_vehicle(
                    account_id: str,
                    _authorized: bool = Depends(authorize_vehicle_create),
                ):
                    # Authorization check passed, proceed with creation
                    return {"message": "Vehicle created", "account_id": account_id}

                @app.put("/vehicles/{vehicle_id}")
                async def update_vehicle(
                    vehicle_id: str,
                    _authorized: bool = Depends(authorize_vehicle_update),
                ):
                    # Authorization check passed, proceed with update
                    return {"message": "Vehicle updated", "vehicle_id": vehicle_id}

            The dependency will:
            1. Extract the user from request.state (set by authentication middleware)
            2. Resolve the domain using your domain_resolver function
            3. Check cache (if enabled) for previous authorization results
            4. Call Custos API to verify authorization
            5. Cache the result (if caching is enabled)
            6. Raise HTTPException(403) if authorization is denied
        """
        # Extract authentication token from request headers
        auth_token = _extract_auth_token(request)

        # Get user from request state (set by authentication middleware)
        if not hasattr(request.state, "user") or request.state.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated",
            )

        user = request.state.user

        # Extract user_id from user object
        # UserResponse has 'id', IntrospectResponse has 'user_id', UserNeedsOnboarding doesn't have id
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
        try:
            domain = await domain_resolver(request)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error resolving domain: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot infer domain: {str(e)}",
            )

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

        # Check cache if enabled (the _get_authorization_cache function already checks the config)
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

        logger.debug(
            f"Calling Custos API to authorize user {user_id} for action {action} on resource {resource} in domain {domain}"
        )

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
                # Cache denied authorization (cache already checked in _get_authorization_cache)
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

            # Cache granted authorization (cache already checked in _get_authorization_cache)
            if cache:
                cache.write(
                    cache_key,
                    {"allowed": True},
                    ttl=settings.authorization_cache_ttl,
                )

        except CustosAuthenticationError as e:
            logger.warning(f"Custos authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
            )
        except CustosValidationError as e:
            logger.warning(f"Custos validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation error: {str(e)}",
            )
        except (CustosClientError, CustosServerError) as e:
            logger.error(f"Custos service error: {e}")
            print(f"Custos service error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authorization service unavailable",
            )
        except CustosError as e:
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
