from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tessera_sdk.infra.auth_token_provider import AuthTokenProvider


class FakeCache:
    """In-memory stand-in for tessera_sdk.infra.cache.Cache."""

    def __init__(self):
        self.store = {}

    def read(self, key):
        return self.store.get(key)

    def write(self, key, value, ttl=None):
        self.store[key] = value
        return True


def test_get_token_uses_identies_client_credentials_when_configured():
    settings = SimpleNamespace(
        identies_api_url="https://identies.example.com",
        identies_client_id="cid",
        identies_client_secret="secret",
    )
    provider = AuthTokenProvider(
        settings=settings,
        audience="https://api.example.com",
        timeout=15,
        cache_service=FakeCache(),
    )

    mock_response = MagicMock()
    mock_response.access_token = "jwt-from-identies"
    mock_response.expires_in = 3600

    with patch("tessera_sdk.infra.auth_token_provider.IdentiesClient") as identies_cls:
        identies_cls.return_value.get_token.return_value = mock_response
        with patch("tessera_sdk.infra.auth_token_provider.M2MTokenClient") as m2m_cls:
            token = provider.get_token()

    assert token == "jwt-from-identies"
    m2m_cls.assert_not_called()
    identies_cls.assert_called_once_with(
        base_url="https://identies.example.com",
        timeout=15,
    )
    identies_cls.return_value.get_token.assert_called_once_with(
        client_id="cid",
        client_secret="secret",
        audience="https://api.example.com",
    )


def test_get_token_caches_identies_token_across_instances():
    settings = SimpleNamespace(
        identies_api_url="https://identies.example.com",
        identies_client_id="cid",
        identies_client_secret="secret",
    )
    shared_cache = FakeCache()

    mock_response = MagicMock()
    mock_response.access_token = "jwt-from-identies"
    mock_response.expires_in = 3600

    with patch("tessera_sdk.infra.auth_token_provider.IdentiesClient") as identies_cls:
        identies_cls.return_value.get_token.return_value = mock_response

        provider_one = AuthTokenProvider(
            settings=settings,
            audience="https://api.example.com",
            cache_service=shared_cache,
        )
        provider_two = AuthTokenProvider(
            settings=settings,
            audience="https://api.example.com",
            cache_service=shared_cache,
        )

        token_one = provider_one.get_token()
        token_two = provider_two.get_token()

    assert token_one == "jwt-from-identies"
    assert token_two == "jwt-from-identies"
    identies_cls.return_value.get_token.assert_called_once()


def test_get_token_force_refresh_bypasses_identies_cache():
    settings = SimpleNamespace(
        identies_api_url="https://identies.example.com",
        identies_client_id="cid",
        identies_client_secret="secret",
    )
    shared_cache = FakeCache()

    mock_response = MagicMock()
    mock_response.access_token = "jwt-from-identies"
    mock_response.expires_in = 3600

    with patch("tessera_sdk.infra.auth_token_provider.IdentiesClient") as identies_cls:
        identies_cls.return_value.get_token.return_value = mock_response

        provider = AuthTokenProvider(
            settings=settings,
            audience="https://api.example.com",
            cache_service=shared_cache,
        )
        provider.get_token()
        provider.get_token(force_refresh=True)

    assert identies_cls.return_value.get_token.call_count == 2


def test_get_token_ignores_blank_identies_client_credentials():
    settings = SimpleNamespace(
        identies_api_url="https://identies.example.com",
        identies_client_id="cid",
        identies_client_secret="   ",
    )
    provider = AuthTokenProvider(settings=settings, cache_service=FakeCache())

    mock_response = MagicMock()
    mock_response.access_token = "m2m-token"

    with patch("tessera_sdk.infra.auth_token_provider.IdentiesClient") as identies_cls:
        with patch("tessera_sdk.infra.auth_token_provider.M2MTokenClient") as m2m_cls:
            m2m_cls.return_value.get_token_sync.return_value = mock_response
            token = provider.get_token()

    assert token == "m2m-token"
    identies_cls.assert_not_called()
    m2m_cls.assert_called_once_with(provider_domain=None, timeout=30)
    m2m_cls.return_value.get_token_sync.assert_called_once_with(
        audience="",
        timeout=30,
        force_refresh=False,
    )


def test_get_token_falls_back_to_m2m_when_missing_client_credentials():
    settings = SimpleNamespace(
        identies_api_url="https://identies.example.com",
        identies_client_id="",
        identies_client_secret="",
    )
    provider = AuthTokenProvider(
        settings=settings,
        provider_domain="example.auth0.com",
        audience="https://my-audience",
        timeout=10,
        cache_service=FakeCache(),
    )

    mock_response = MagicMock()
    mock_response.access_token = "m2m-token"

    with patch("tessera_sdk.infra.auth_token_provider.IdentiesClient") as identies_cls:
        with patch("tessera_sdk.infra.auth_token_provider.M2MTokenClient") as m2m_cls:
            m2m_cls.return_value.get_token_sync.return_value = mock_response
            token = provider.get_token()

    assert token == "m2m-token"
    identies_cls.assert_not_called()
    m2m_cls.assert_called_once_with(provider_domain="example.auth0.com", timeout=10)
    m2m_cls.return_value.get_token_sync.assert_called_once_with(
        audience="https://my-audience",
        timeout=10,
        force_refresh=False,
    )


def test_get_token_propagates_m2m_errors():
    settings = SimpleNamespace(
        identies_api_url="https://identies.example.com",
        identies_client_id="",
        identies_client_secret="",
    )
    provider = AuthTokenProvider(settings=settings, cache_service=FakeCache())

    with patch("tessera_sdk.infra.auth_token_provider.M2MTokenClient") as m2m_cls:
        m2m_cls.return_value.get_token_sync.side_effect = ValueError(
            "missing credentials"
        )
        with pytest.raises(ValueError, match="missing credentials"):
            provider.get_token()
