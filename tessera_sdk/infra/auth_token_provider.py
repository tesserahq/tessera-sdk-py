from __future__ import annotations

from typing import Optional

from ..clients.identies import IdentiesClient
from ..config import Settings, get_settings
from .cache import Cache
from .m2m_token import M2MTokenClient


class AuthTokenProvider:
    """
    Resolve an API token using Identies OAuth client_credentials when
    ``IDENTIES_CLIENT_ID`` and ``IDENTIES_CLIENT_SECRET`` are set, otherwise
    Auth0 (or configured) M2M.

    Tokens are cached (Redis-backed) keyed by provider/client id/audience, so
    repeated calls reuse a valid token instead of hitting ``/oauth/token`` on
    every call. A new ``AuthTokenProvider`` instance still hits the shared
    cache, since the cache lives outside the instance.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        provider_domain: Optional[str] = None,
        audience: str = "",
        timeout: int = 30,
        cache_service: Optional[Cache] = None,
        cache_buffer_seconds: int = 60,
    ):
        self.settings = settings or get_settings()
        self.provider_domain = provider_domain
        self.audience = audience
        self.timeout = timeout
        self.cache_service = cache_service or Cache("auth_token")
        self.cache_buffer_seconds = cache_buffer_seconds

    def get_token(self, force_refresh: bool = False) -> str:
        """
        Return an access token from Identies ``POST /oauth/token`` when both
        client id and secret are configured; otherwise fetch an M2M token.

        Uses a cached token when available and not expired. Set
        ``force_refresh=True`` to bypass the cache.
        """
        client_id = (self.settings.identies_client_id or "").strip()
        client_secret = (self.settings.identies_client_secret or "").strip()
        if client_id and client_secret:
            audience = self.audience or self.settings.identies_client_audience
            cache_key = f"identies:{client_id}:{audience}"

            if not force_refresh:
                cached_token = self._get_cached_access_token(cache_key)
                if cached_token:
                    return cached_token

            identies = IdentiesClient(
                base_url=self.settings.identies_api_url,
                timeout=self.timeout,
            )
            response = identies.get_token(
                client_id=client_id,
                client_secret=client_secret,
                audience=audience,
            )
            self._cache_access_token(
                cache_key, response.access_token, response.expires_in
            )
            return response.access_token

        m2m_client = M2MTokenClient(
            provider_domain=self.provider_domain, timeout=self.timeout
        )
        response = m2m_client.get_token_sync(
            audience=self.audience,
            timeout=self.timeout,
            force_refresh=force_refresh,
        )
        return response.access_token

    def _get_cached_access_token(self, cache_key: str) -> Optional[str]:
        try:
            cached = self.cache_service.read(cache_key)
        except Exception:
            return None
        if cached:
            return cached.get("access_token")
        return None

    def _cache_access_token(
        self, cache_key: str, access_token: str, expires_in: int
    ) -> None:
        ttl = max(expires_in - self.cache_buffer_seconds, 1)
        self.cache_service.write(cache_key, {"access_token": access_token}, ttl=ttl)
