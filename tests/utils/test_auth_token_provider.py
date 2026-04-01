from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tessera_sdk.infra.auth_token_provider import AuthTokenProvider


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
    )

    mock_response = MagicMock()
    mock_response.access_token = "jwt-from-identies"

    with patch("tessera_sdk.infra.auth_token_provider.IdentiesClient") as identies_cls:
        identies_cls.return_value.get_token.return_value = mock_response
        with patch("tessera_sdk.infra.auth_token_provider.get_m2m_token_sync") as m2m:
            token = provider.get_token()

    assert token == "jwt-from-identies"
    m2m.assert_not_called()
    identies_cls.assert_called_once_with(
        base_url="https://identies.example.com",
        timeout=15,
    )
    identies_cls.return_value.get_token.assert_called_once_with(
        client_id="cid",
        client_secret="secret",
        audience="https://api.example.com",
    )


def test_get_token_ignores_blank_identies_client_credentials():
    settings = SimpleNamespace(
        identies_api_url="https://identies.example.com",
        identies_client_id="cid",
        identies_client_secret="   ",
    )
    provider = AuthTokenProvider(settings=settings)

    with patch("tessera_sdk.infra.auth_token_provider.IdentiesClient") as identies_cls:
        with patch(
            "tessera_sdk.infra.auth_token_provider.get_m2m_token_sync",
            return_value="m2m-token",
        ) as m2m:
            token = provider.get_token()

    assert token == "m2m-token"
    identies_cls.assert_not_called()
    m2m.assert_called_once_with(
        audience="",
        provider_domain=None,
        timeout=30,
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
    )

    with patch("tessera_sdk.infra.auth_token_provider.IdentiesClient") as identies_cls:
        with patch(
            "tessera_sdk.infra.auth_token_provider.get_m2m_token_sync",
            return_value="m2m-token",
        ) as m2m:
            token = provider.get_token()

    assert token == "m2m-token"
    identies_cls.assert_not_called()
    m2m.assert_called_once_with(
        audience="https://my-audience",
        provider_domain="example.auth0.com",
        timeout=10,
    )


def test_get_token_propagates_m2m_errors():
    settings = SimpleNamespace(
        identies_api_url="https://identies.example.com",
        identies_client_id="",
        identies_client_secret="",
    )
    provider = AuthTokenProvider(settings=settings)

    with patch(
        "tessera_sdk.infra.auth_token_provider.get_m2m_token_sync",
        side_effect=ValueError("missing credentials"),
    ):
        with pytest.raises(ValueError, match="missing credentials"):
            provider.get_token()
