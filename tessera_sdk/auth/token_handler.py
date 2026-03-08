import jwt
from typing import TYPE_CHECKING, Optional

from tessera_sdk.config import get_settings
from tessera_sdk.base.exceptions import UnauthorizedException
from tessera_sdk.identies import IdentiesClient
import logging

logger = logging.getLogger(__name__)


def _is_api_key(token: str) -> bool:
    """Return True if the token looks like an API key (ak_<key_id>.<secret>)."""
    return bool(token and token.startswith("ak_") and "." in token)


class TokenHandler:
    """Verifies JWT tokens and API keys, returning a payload-like dict for both."""

    def __init__(self):
        self.settings = get_settings()
        self.identies_client = IdentiesClient(
            timeout=int(self.settings.tesserasdk_auth_middleware_timeout),
        )

        providers = self.settings.get_auth_providers()
        if not providers:
            raise ValueError("AUTH_PROVIDERS_JSON or OIDC settings are not configured.")

        self.providers: list[dict] = []
        for provider in providers:
            jwks_url = provider.get("jwks_url")
            if not jwks_url:
                continue
            issuer = provider.get("issuer")
            audience = provider.get("audience")
            self.providers.append(
                {
                    "jwks_url": jwks_url,
                    "issuer": issuer,
                    "audience": audience,
                    "jwks_client": jwt.PyJWKClient(jwks_url, cache_keys=True),
                }
            )

    def verify(self, token: str) -> dict:
        """
        Verify token as either an API key or JWT.
        Returns a payload-like dict with at least 'sub' for user resolution.
        """
        if not token:
            raise UnauthorizedException(detail="Missing or invalid token")

        if _is_api_key(token):
            return self._verify_api_key(token)

        return self._verify_jwt(token)

    def _verify_api_key(self, token: str) -> dict:
        """Verify API key via Identies introspect; return payload with 'sub' for user resolution."""
        if not self.identies_client:
            raise UnauthorizedException(detail="API key verification not configured")
        self.identies_client.session.headers.update(
            {"Authorization": f"Bearer {token}"}
        )
        try:
            response = self.identies_client.introspect()
            if response.active and response.user_id is not None:
                return {"sub": str(response.user_id)}
            raise UnauthorizedException(detail="Invalid or expired API key")
        finally:
            if "Authorization" in self.identies_client.session.headers:
                del self.identies_client.session.headers["Authorization"]

    def _verify_jwt(self, token: str) -> dict:
        """Verify JWT and return decoded payload."""
        last_error: Exception | None = None

        for provider in self.providers:
            issuer = provider.get("issuer")
            audience = provider.get("audience")
            try:
                logger.info(f"Verifying JWT with provider: {provider['jwks_url']}")
                signing_key = (
                    provider["jwks_client"].get_signing_key_from_jwt(token).key
                )
            except jwt.exceptions.PyJWKClientError as error:
                last_error = error
                continue
            except jwt.exceptions.DecodeError as error:
                last_error = error
                continue

            try:
                payload = jwt.decode(
                    token,
                    signing_key,
                    algorithms=self.settings.oidc_algorithms,
                    audience=audience,
                    issuer=issuer,
                )
                return payload
            except Exception as error:
                last_error = error
                continue

        if last_error:
            raise UnauthorizedException(str(last_error))
        raise UnauthorizedException("Unable to verify token")

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
