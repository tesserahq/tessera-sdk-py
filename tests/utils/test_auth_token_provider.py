from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tessera_sdk.infra.auth_token_provider import AuthTokenProvider


def test_get_token_returns_identies_system_account_api_key_from_settings():
    settings = SimpleNamespace(identies_system_account_api_key="env-token")
    provider = AuthTokenProvider(settings=settings)

    with patch("tessera_sdk.infra.auth_token_provider.get_m2m_token_sync") as m2m:
        token = provider.get_token()

    assert token == "env-token"
    m2m.assert_not_called()


def test_get_token_ignores_blank_identies_system_account_api_key():
    settings = SimpleNamespace(identies_system_account_api_key="   ")
    provider = AuthTokenProvider(settings=settings)

    with patch(
        "tessera_sdk.infra.auth_token_provider.get_m2m_token_sync",
        return_value="m2m-token",
    ) as m2m:
        token = provider.get_token()

    assert token == "m2m-token"
    m2m.assert_called_once_with(
        audience="",
        provider_domain=None,
        timeout=30,
    )


def test_get_token_falls_back_to_m2m_when_missing_key():
    settings = SimpleNamespace(identies_system_account_api_key="")
    provider = AuthTokenProvider(
        settings=settings,
        provider_domain="example.auth0.com",
        audience="https://my-audience",
        timeout=10,
    )

    with patch(
        "tessera_sdk.infra.auth_token_provider.get_m2m_token_sync",
        return_value="m2m-token",
    ) as m2m:
        token = provider.get_token()

    assert token == "m2m-token"
    m2m.assert_called_once_with(
        audience="https://my-audience",
        provider_domain="example.auth0.com",
        timeout=10,
    )


def test_get_token_propagates_m2m_errors():
    settings = SimpleNamespace(identies_system_account_api_key="")
    provider = AuthTokenProvider(settings=settings)

    with patch(
        "tessera_sdk.infra.auth_token_provider.get_m2m_token_sync",
        side_effect=ValueError("missing credentials"),
    ):
        with pytest.raises(ValueError, match="missing credentials"):
            provider.get_token()
