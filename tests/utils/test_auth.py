from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from tessera_sdk.auth.token_handler import TokenHandler
from tessera_sdk.base.exceptions import UnauthorizedException


def _mock_settings():
    def get_auth_providers():
        return [
            {
                "jwks_url": "https://test.oidc.com/.well-known/jwks.json",
                "issuer": "https://test.oidc.com/",
                "audience": "https://test-api",
            }
        ]

    return SimpleNamespace(
        oidc_domain="test.oidc.com",
        oidc_algorithms="RS256",
        oidc_api_audience="https://test-api",
        oidc_issuer="https://test.oidc.com/",
        get_auth_providers=get_auth_providers,
    )


class DummyJWKS:
    def __init__(self, key="signing-key"):
        self.key = key

    def get_signing_key_from_jwt(self, token):
        return SimpleNamespace(key=self.key)


class DummyJWKSFailure:
    def get_signing_key_from_jwt(self, token):
        raise jwt.exceptions.PyJWKClientError("bad key")


@patch("tessera_sdk.auth.token_handler.get_settings", side_effect=_mock_settings)
def test_verify_token_jwks_error_returns_http_403(mock_get_settings):
    with patch(
        "tessera_sdk.auth.token_handler.jwt.PyJWKClient",
        return_value=DummyJWKSFailure(),
    ):
        handler = TokenHandler()

    with pytest.raises(HTTPException) as exc:
        handler.verify("token")

    # UnauthorizedException uses 403 in this code path
    assert exc.value.status_code == 403


@patch("tessera_sdk.auth.token_handler.get_settings", side_effect=_mock_settings)
def test_verify_token_decode_error_returns_unauthorized(mock_get_settings):
    with (
        patch(
            "tessera_sdk.auth.token_handler.jwt.PyJWKClient",
            return_value=DummyJWKS(),
        ),
        patch(
            "tessera_sdk.auth.token_handler.jwt.decode",
            side_effect=Exception("bad"),
        ),
    ):
        handler = TokenHandler()

        with pytest.raises(UnauthorizedException) as exc:
            handler.verify("token")

    assert exc.value.status_code == 403


@patch("tessera_sdk.auth.token_handler.get_settings", side_effect=_mock_settings)
def test_verify_token_returns_payload(mock_get_settings):
    payload = {"sub": "external-2"}

    with (
        patch(
            "tessera_sdk.auth.token_handler.jwt.PyJWKClient",
            return_value=DummyJWKS(),
        ),
        patch(
            "tessera_sdk.auth.token_handler.jwt.decode",
            return_value=payload,
        ),
    ):
        handler = TokenHandler()
        result = handler.verify("token")

    assert result == payload
    assert result["sub"] == "external-2"
