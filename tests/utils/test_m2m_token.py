import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from tessera_sdk.utils.m2m_token import M2MTokenClient, M2MTokenResponse


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture
def settings():
    return SimpleNamespace(
        oidc_domain="example.com",
        service_account_client_id="client-id",
        service_account_client_secret="secret",
        oidc_api_audience="audience",
    )


@pytest.fixture
def cache():
    cache_instance = Mock()
    cache_instance.read.return_value = None
    cache_instance.delete.return_value = True
    return cache_instance


def test_prepare_token_request_uses_settings(settings, cache):
    with patch(
        "tessera_sdk.utils.m2m_token.get_settings",
        return_value=settings,
    ):
        client = M2MTokenClient(cache_service=cache)
        payload, headers = client._prepare_token_request()

    assert payload.client_id == "client-id"
    assert payload.client_secret == "secret"
    assert payload.audience == "audience"
    assert headers == {"Content-Type": "application/json"}


def test_prepare_token_request_missing_credentials(settings, cache):
    settings.service_account_client_id = ""
    settings.service_account_client_secret = ""
    with patch(
        "tessera_sdk.utils.m2m_token.get_settings",
        return_value=settings,
    ):
        client = M2MTokenClient(cache_service=cache)
        with pytest.raises(ValueError):
            client._prepare_token_request()


def test_process_token_response_requires_fields(settings, cache):
    with patch(
        "tessera_sdk.utils.m2m_token.get_settings",
        return_value=settings,
    ):
        client = M2MTokenClient(cache_service=cache)
        with pytest.raises(ValueError):
            client._process_token_response({"access_token": "token"})


def test_request_token_resets_timeout(settings, cache):
    with patch(
        "tessera_sdk.utils.m2m_token.get_settings",
        return_value=settings,
    ):
        client = M2MTokenClient(cache_service=cache)

    response = {
        "access_token": "token",
        "token_type": "Bearer",
        "expires_in": 120,
    }
    with patch.object(
        client,
        "_make_request",
        return_value=DummyResponse(response),
    ):
        result = client._request_token(timeout=5)

    assert result.access_token == "token"
    assert client.timeout == 30


@pytest.mark.anyio
async def test_get_token_returns_cached(settings, cache):
    cached = M2MTokenResponse(
        access_token="cached",
        token_type="Bearer",
        expires_in=60,
    )
    cache.read.return_value = json.dumps(cached.model_dump())

    with patch(
        "tessera_sdk.utils.m2m_token.get_settings",
        return_value=settings,
    ):
        client = M2MTokenClient(cache_service=cache)
        result = await client.get_token()

    assert result.access_token == "cached"


@pytest.mark.anyio
async def test_get_token_force_refresh(settings, cache):
    token = M2MTokenResponse(access_token="fresh", token_type="Bearer", expires_in=60)

    with patch(
        "tessera_sdk.utils.m2m_token.get_settings",
        return_value=settings,
    ):
        client = M2MTokenClient(cache_service=cache)

    with patch.object(
        client,
        "_request_token",
        return_value=token,
    ) as mock_request:
        result = await client.get_token(force_refresh=True)

    mock_request.assert_called_once()
    assert result.access_token == "fresh"


def test_cache_token_writes_with_ttl(settings, cache):
    with patch(
        "tessera_sdk.utils.m2m_token.get_settings",
        return_value=settings,
    ):
        client = M2MTokenClient(cache_service=cache, cache_buffer_seconds=10)

    token = M2MTokenResponse(access_token="token", token_type="Bearer", expires_in=60)
    client._cache_token(token, "key")

    cache.write.assert_called_once()
    ttl = cache.write.call_args.kwargs.get("ttl")
    assert ttl == 50


def test_clear_cache(settings, cache):
    with patch(
        "tessera_sdk.utils.m2m_token.get_settings",
        return_value=settings,
    ):
        client = M2MTokenClient(cache_service=cache)
        assert client.clear_cache() is True


@pytest.mark.anyio
async def test_get_token_missing_provider_domain(cache):
    settings = SimpleNamespace(
        oidc_domain="",
        service_account_client_id="client-id",
        service_account_client_secret="secret",
        oidc_api_audience="audience",
    )

    with patch(
        "tessera_sdk.utils.m2m_token.get_settings",
        return_value=settings,
    ):
        with pytest.raises(ValueError):
            M2MTokenClient(cache_service=cache)
