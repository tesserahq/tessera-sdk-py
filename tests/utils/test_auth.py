from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from tessera_sdk.schemas.user import UserNeedsOnboarding
from tessera_sdk.utils.auth import (
    UnauthenticatedException,
    UnauthorizedException,
    VerifyToken,
    verify_token_dependency,
)


class DummyJWKS:
    def __init__(self, key="signing-key"):
        self.key = key

    def get_signing_key_from_jwt(self, token):
        return SimpleNamespace(key=self.key)


class DummyJWKSFailure:
    def get_signing_key_from_jwt(self, token):
        raise jwt.exceptions.PyJWKClientError("bad key")


def test_verify_token_dependency_sets_user():
    request = SimpleNamespace(state=SimpleNamespace())

    with (
        patch("tessera_sdk.utils.auth.jwt.PyJWKClient", return_value=DummyJWKS()),
        patch(
            "tessera_sdk.utils.auth.VerifyToken.verify",
            return_value={"id": "user-1"},
        ),
    ):
        verify_token_dependency(request, "token", user_service_factory=lambda: None)

    assert request.state.user == {"id": "user-1"}


def test_verify_token_empty_raises_unauthenticated():
    with patch("tessera_sdk.utils.auth.jwt.PyJWKClient", return_value=DummyJWKS()):
        verifier = VerifyToken(user_service_factory=lambda: None)

    with pytest.raises(UnauthenticatedException):
        verifier.verify("")


def test_verify_token_jwks_error_returns_http_401():
    with patch(
        "tessera_sdk.utils.auth.jwt.PyJWKClient", return_value=DummyJWKSFailure()
    ):
        verifier = VerifyToken(user_service_factory=lambda: None)

    with pytest.raises(HTTPException) as exc:
        verifier.verify("token")

    assert exc.value.status_code == 401


def test_verify_token_decode_error_returns_unauthorized():
    payload = {"sub": "external-1"}

    with (
        patch("tessera_sdk.utils.auth.jwt.PyJWKClient", return_value=DummyJWKS()),
        patch(
            "tessera_sdk.utils.auth.jwt.decode",
            side_effect=Exception("bad"),
        ),
    ):
        verifier = VerifyToken(user_service_factory=lambda: None)

        with pytest.raises(UnauthorizedException) as exc:
            verifier.verify("token")

    assert exc.value.status_code == 403


def test_verify_token_returns_onboarding_user():
    payload = {"sub": "external-2"}

    class DummyUserService:
        def get_user_by_external_id(self, external_id):
            return None

    with (
        patch("tessera_sdk.utils.auth.jwt.PyJWKClient", return_value=DummyJWKS()),
        patch(
            "tessera_sdk.utils.auth.jwt.decode",
            return_value=payload,
        ),
    ):
        verifier = VerifyToken(user_service_factory=lambda: DummyUserService())
        result = verifier.verify("token")

    assert isinstance(result, UserNeedsOnboarding)
    assert result.external_id == "external-2"
    assert result.needs_onboarding is True
