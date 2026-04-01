from __future__ import annotations

from typing import Optional

from ..clients.identies import IdentiesClient
from ..config import Settings, get_settings
from .m2m_token import get_m2m_token_sync


class AuthTokenProvider:
    """
    Resolve an API token using Identies OAuth client_credentials when
    ``IDENTIES_CLIENT_ID`` and ``IDENTIES_CLIENT_SECRET`` are set, otherwise
    Auth0 (or configured) M2M.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        provider_domain: Optional[str] = None,
        audience: str = "",
        timeout: int = 30,
    ):
        self.settings = settings or get_settings()
        self.provider_domain = provider_domain
        self.audience = audience
        self.timeout = timeout

    def get_token(self) -> str:
        """
        Return an access token from Identies ``POST /oauth/token`` when both
        client id and secret are configured; otherwise fetch an M2M token.
        """
        client_id = (self.settings.identies_client_id or "").strip()
        client_secret = (self.settings.identies_client_secret or "").strip()
        if client_id and client_secret:
            identies = IdentiesClient(
                base_url=self.settings.identies_api_url,
                timeout=self.timeout,
            )
            return identies.get_token(
                client_id=client_id,
                client_secret=client_secret,
                audience=self.audience or self.settings.identies_client_audience,
            ).access_token

        return get_m2m_token_sync(
            audience=self.audience,
            provider_domain=self.provider_domain,
            timeout=self.timeout,
        )
