import jwt
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer

from tessera_sdk.config import get_settings
from tessera_sdk.schemas.user import UserNeedsOnboarding

security = HTTPBearer()


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str, **kwargs):
        """Returns HTTP 403"""
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthenticatedException(HTTPException):
    def __init__(self):
        """Returns HTTP 401"""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication"
        )


def verify_token_dependency(
    request: Request,
    token: str,
    user_service_factory,
):
    """
    Verify a JWT token and set the user in request state.

    Args:
        request: The FastAPI request object
        token: The JWT token to verify
        db: Optional database session (if provided, will be used directly)
        database_manager: Optional DatabaseManager instance (used to create session if db is None)
    """

    verifier = VerifyToken(user_service_factory)
    user = verifier.verify(token)
    request.state.user = user


async def get_current_user(request: Request):
    if not hasattr(request.state, "user") or request.state.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return request.state.user


class VerifyToken:
    """Does all the token verification using PyJWT"""

    def __init__(self, user_service_factory):
        self.config = get_settings()
        self.user_service_factory = user_service_factory

        if self.config.oidc_domain is None:
            raise ValueError("oidc domain is not set in the configuration.")

        # This gets the JWKS from a given URL and does processing so you can
        # use any of the keys available
        jwks_url = f"https://{self.config.oidc_domain}/.well-known/jwks.json"
        self.jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True)

    def verify(self, token: str):
        # Check if token is None or empty
        if not token:
            raise UnauthenticatedException()

        # This gets the 'kid' from the passed token

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token).key
        except jwt.exceptions.PyJWKClientError as error:
            # raise UnauthorizedException(str(error))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
            )
        except jwt.exceptions.DecodeError as error:
            # raise UnauthorizedException(str(error))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
            )

        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=self.config.oidc_algorithms,
                audience=self.config.oidc_api_audience,
                issuer=self.config.oidc_issuer,
            )
        except Exception as error:
            raise UnauthorizedException(str(error))

        # Extract user ID from JWT payload
        external_user_id = payload["sub"]

        user_service = self.user_service_factory()

        # User not in cache or cache was invalid, check database
        user = user_service.get_user_by_external_id(external_user_id)

        if user:
            # User exists in database, cache the existence
            return user
        else:
            # User doesn't exist, return None - onboarding will be handled by UserOnboardingMiddleware
            return UserNeedsOnboarding(
                external_id=external_user_id,
                needs_onboarding=True,
            )
