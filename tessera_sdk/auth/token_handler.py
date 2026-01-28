import jwt
from fastapi import HTTPException, status
from tessera_sdk.config import get_settings
from tessera_sdk.base.exceptions import UnauthorizedException


class TokenHandler:
    """Does all the token verification using PyJWT"""

    def __init__(self):
        self.config = get_settings()

        if self.config.oidc_domain is None:
            raise ValueError("oidc domain is not set in the configuration.")

        # This gets the JWKS from a given URL and does processing so you can
        # use any of the keys available
        jwks_url = f"https://{self.config.oidc_domain}/.well-known/jwks.json"
        self.jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True)

    def has_bearer_token_header(self, headers) -> bool:
        """
        Check if the request has a bearer token header (supports Mapping or Dict).
        Accepts both "Authorization" and "authorization" header keys,
        case-insensitive in practice.
        """
        # Convert header keys to lowercase for case-insensitive match
        # Starlette headers (and some servers) use all-lowercase keys
        authorization = None
        if hasattr(headers, "get"):
            # Try common case-insensitive approaches
            authorization = headers.get("authorization")
            if not authorization:
                authorization = headers.get("Authorization")
        else:
            # fallback for objects that don't implement .get()
            if "authorization" in headers:
                authorization = headers["authorization"]
            elif "Authorization" in headers:
                authorization = headers["Authorization"]
            else:
                authorization = None

        if (
            not authorization
            or not isinstance(authorization, str)
            or not authorization.strip().lower().startswith("bearer ")
        ):
            return False
        return True

    def get_bearer_token(self, headers) -> str:
        """
        Get the bearer token from the request headers (supports Mapping or Dict).
        Accepts both "Authorization" and "authorization" header keys,
        case-insensitive in practice.
        """
        authorization = None
        if hasattr(headers, "get"):
            authorization = headers.get("authorization")
            if not authorization:
                authorization = headers.get("Authorization")
        else:
            if "authorization" in headers:
                authorization = headers["authorization"]
            elif "Authorization" in headers:
                authorization = headers["Authorization"]
            else:
                authorization = ""

        if (
            not authorization
            or not isinstance(authorization, str)
            or not authorization.strip().lower().startswith("bearer ")
        ):
            return ""

        # Remove "Bearer " (case-insensitive) from value
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return ""

    def verify(self, token: str) -> dict:
        # Check if token is None or empty
        if not token:
            raise UnauthorizedException(detail="Missing or invalid token")
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

        return payload
