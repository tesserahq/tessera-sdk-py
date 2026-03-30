from __future__ import annotations

from typing import Optional

from ..config import Settings, get_settings
from .m2m_token import get_m2m_token_sync


class AuthTokenProvider:
    """
    Resolve an API token using env-var first and Auth0 M2M fallback.
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
        Return `IDENTIES_SYSTEM_ACCOUNT_API_KEY` when configured, otherwise fetch M2M token.
        """
        env_token = self.settings.identies_system_account_api_key
        if env_token and isinstance(env_token, str):
            stripped_token = env_token.strip()
            if stripped_token:
                return stripped_token

        return get_m2m_token_sync(
            audience=self.audience,
            provider_domain=self.provider_domain,
            timeout=self.timeout,
        )
