import logging
import time
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from tessera_sdk.server.auth.token_handler import TokenHandler
from tessera_sdk.server.exceptions import UnauthorizedException

AUTH0 = {
    "jwks_url": "https://auth.example.test/.well-known/jwks.json",
    "issuer": "https://auth.example.test/",
    "audience": "https://api.example.test",
}
IDENTIES = {
    "jwks_url": "http://identies-api:8000/.well-known/jwks.json",
    "issuer": "https://identies.example.test/",
    "audience": "https://identies.example.test/",
}


def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


KEYS = {"auth0-1": _key(), "identies-1": _key(), "identies-2": _key()}
KEYS_BY_URL = {
    AUTH0["jwks_url"]: ["auth0-1"],
    IDENTIES["jwks_url"]: ["identies-1", "identies-2"],
}


class RecordingJWKS:
    """Stands in for PyJWKClient: resolves the token's kid and records lookups."""

    calls: list[str] = []

    def __init__(self, url, **_kwargs):
        self.url = url

    def get_signing_key_from_jwt(self, token):
        RecordingJWKS.calls.append(self.url)
        kid = jwt.get_unverified_header(token).get("kid")
        if kid not in KEYS_BY_URL[self.url]:
            raise jwt.exceptions.PyJWKClientError(
                f'Unable to find a signing key that matches: "{kid}"'
            )
        return SimpleNamespace(key=KEYS[kid].public_key())


def _settings():
    return SimpleNamespace(
        oidc_algorithms=["RS256"],
        tesserasdk_auth_middleware_timeout=3,
        get_auth_providers=lambda: [dict(AUTH0), dict(IDENTIES)],
    )


def _token(kid, provider, *, signing_kid=None, **overrides):
    claims = {
        "sub": "user-1",
        "iss": provider["issuer"],
        "aud": provider["audience"],
        "exp": int(time.time()) + 300,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    headers = {"kid": kid} if kid else {}
    return jwt.encode(
        claims, KEYS[signing_kid or kid], algorithm="RS256", headers=headers
    )


@pytest.fixture
def handler():
    RecordingJWKS.calls = []
    with (
        patch(
            "tessera_sdk.server.auth.token_handler.get_settings",
            side_effect=_settings,
        ),
        patch(
            "tessera_sdk.server.auth.token_handler.jwt.PyJWKClient",
            side_effect=RecordingJWKS,
        ),
    ):
        yield TokenHandler()


def test_second_provider_token_skips_first_provider_without_warnings(handler, caplog):
    caplog.set_level(logging.DEBUG)

    payload = handler.verify(_token("identies-1", IDENTIES))

    assert payload["sub"] == "user-1"
    assert RecordingJWKS.calls == [IDENTIES["jwks_url"]]
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_first_provider_token_is_accepted(handler):
    payload = handler.verify(_token("auth0-1", AUTH0))

    assert payload["iss"] == AUTH0["issuer"]
    assert RecordingJWKS.calls == [AUTH0["jwks_url"]]


def test_rotated_key_is_accepted(handler):
    payload = handler.verify(_token("identies-2", IDENTIES))

    assert payload["sub"] == "user-1"


def test_unknown_issuer_is_rejected_without_jwks_lookup(handler):
    with pytest.raises(UnauthorizedException):
        handler.verify(_token("auth0-1", AUTH0, iss="https://evil.example.test/"))

    assert RecordingJWKS.calls == []


@pytest.mark.parametrize(
    "token_factory",
    [
        pytest.param(
            lambda: _token("identies-1", IDENTIES, exp=int(time.time()) - 60),
            id="expired",
        ),
        pytest.param(
            lambda: _token("identies-1", IDENTIES, aud="https://other.example.test"),
            id="wrong-audience",
        ),
        pytest.param(
            lambda: _token("identies-1", IDENTIES, signing_kid="auth0-1"),
            id="invalid-signature",
        ),
        pytest.param(
            lambda: _token("unknown-kid", IDENTIES, signing_kid="identies-1"),
            id="unknown-kid",
        ),
        pytest.param(
            lambda: _token(None, IDENTIES, signing_kid="identies-1"), id="missing-kid"
        ),
        pytest.param(
            lambda: _token("identies-1", IDENTIES, iss=None), id="missing-iss"
        ),
        pytest.param(lambda: "not-a-jwt", id="malformed"),
    ],
)
def test_invalid_tokens_are_rejected_without_error_logs(handler, caplog, token_factory):
    caplog.set_level(logging.DEBUG)
    token = token_factory()

    with pytest.raises(UnauthorizedException):
        handler.verify(token)

    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
