from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from tessera_sdk.custos.exceptions import (
    CustosAuthenticationError,
    CustosClientError,
    CustosError,
    CustosServerError,
    CustosValidationError,
)
from tessera_sdk.utils import authorization_dependency
from tessera_sdk.utils.authorization_dependency import authorize


class DummyAuthorizeResponse:
    def __init__(self, allowed: bool):
        self.allowed = allowed


def _make_request(user=None, headers=None):
    if headers is None:
        headers = {}
    return SimpleNamespace(headers=headers, state=SimpleNamespace(user=user))


@pytest.mark.anyio
async def test_authorize_requires_auth_header():
    dependency = authorize("read", "resource", lambda _request: "domain")
    request = _make_request(user=SimpleNamespace(id="user-1"))

    with pytest.raises(HTTPException) as exc:
        await dependency(request)

    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_authorize_requires_user():
    dependency = authorize("read", "resource", lambda _request: "domain")
    request = _make_request(headers={"Authorization": "Bearer token"})

    with pytest.raises(HTTPException) as exc:
        await dependency(request)

    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_authorize_uses_user_id_attribute():
    async def resolve_domain(_request):
        return "domain"

    settings = SimpleNamespace(
        custos_api_url="https://custos.example.com",
        authorization_cache_enabled=False,
        authorization_cache_ttl=300,
    )
    request = _make_request(
        user=SimpleNamespace(user_id="user-1"),
        headers={"Authorization": "Bearer token"},
    )

    with (
        patch(
            "tessera_sdk.utils.authorization_dependency.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency.CustosClient.authorize",
            return_value=DummyAuthorizeResponse(True),
        ),
    ):
        dependency = authorize("read", "resource", resolve_domain)
        result = await dependency(request)

    assert result is True


@pytest.mark.anyio
async def test_authorize_domain_resolver_error():
    async def resolve_domain(_request):
        raise ValueError("boom")

    settings = SimpleNamespace(
        custos_api_url="https://custos.example.com",
        authorization_cache_enabled=False,
        authorization_cache_ttl=300,
    )
    request = _make_request(
        user=SimpleNamespace(id="user-1"),
        headers={"Authorization": "Bearer token"},
    )

    with patch(
        "tessera_sdk.utils.authorization_dependency.get_settings",
        return_value=settings,
    ):
        dependency = authorize("read", "resource", resolve_domain)

        with pytest.raises(HTTPException) as exc:
            await dependency(request)

    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_authorize_cache_hit_allows():
    async def resolve_domain(_request):
        return "domain"

    cache = Mock()
    cache.read.return_value = {"authorized": True}
    settings = SimpleNamespace(
        custos_api_url="https://custos.example.com",
        authorization_cache_enabled=True,
        authorization_cache_ttl=300,
    )
    request = _make_request(
        user=SimpleNamespace(id="user-1"),
        headers={"Authorization": "Bearer token"},
    )

    with (
        patch(
            "tessera_sdk.utils.authorization_dependency.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency._get_authorization_cache",
            return_value=cache,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency.CustosClient.authorize",
        ) as mock_authorize,
    ):
        dependency = authorize("read", "resource", resolve_domain)
        result = await dependency(request)

    mock_authorize.assert_not_called()
    assert result is True


@pytest.mark.anyio
async def test_authorize_cache_hit_denies():
    async def resolve_domain(_request):
        return "domain"

    cache = Mock()
    cache.read.return_value = {"authorized": False}
    settings = SimpleNamespace(
        custos_api_url="https://custos.example.com",
        authorization_cache_enabled=True,
        authorization_cache_ttl=300,
    )
    request = _make_request(
        user=SimpleNamespace(id="user-1"),
        headers={"Authorization": "Bearer token"},
    )

    with (
        patch(
            "tessera_sdk.utils.authorization_dependency.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency._get_authorization_cache",
            return_value=cache,
        ),
    ):
        dependency = authorize("read", "resource", resolve_domain)

        with pytest.raises(HTTPException) as exc:
            await dependency(request)

    assert exc.value.status_code == 403


@pytest.mark.anyio
async def test_authorize_denied_writes_cache():
    async def resolve_domain(_request):
        return "domain"

    cache = Mock()
    cache.read.return_value = None
    settings = SimpleNamespace(
        custos_api_url="https://custos.example.com",
        authorization_cache_enabled=True,
        authorization_cache_ttl=300,
    )
    request = _make_request(
        user=SimpleNamespace(id="user-1"),
        headers={"Authorization": "Bearer token"},
    )

    with (
        patch(
            "tessera_sdk.utils.authorization_dependency.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency._get_authorization_cache",
            return_value=cache,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency.CustosClient.authorize",
            return_value=DummyAuthorizeResponse(False),
        ),
    ):
        dependency = authorize("read", "resource", resolve_domain)

        with pytest.raises(HTTPException) as exc:
            await dependency(request)

    cache.write.assert_called_once()
    assert exc.value.status_code == 403


@pytest.mark.anyio
async def test_authorize_allowed_writes_cache():
    async def resolve_domain(_request):
        return "domain"

    cache = Mock()
    cache.read.return_value = None
    settings = SimpleNamespace(
        custos_api_url="https://custos.example.com",
        authorization_cache_enabled=True,
        authorization_cache_ttl=300,
    )
    request = _make_request(
        user=SimpleNamespace(id="user-1"),
        headers={"Authorization": "Bearer token"},
    )

    with (
        patch(
            "tessera_sdk.utils.authorization_dependency.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency._get_authorization_cache",
            return_value=cache,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency.CustosClient.authorize",
            return_value=DummyAuthorizeResponse(True),
        ),
    ):
        dependency = authorize("read", "resource", resolve_domain)
        result = await dependency(request)

    cache.write.assert_called_once()
    assert result is True


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error, status_code",
    [
        (CustosAuthenticationError("nope"), 401),
        (CustosValidationError("bad"), 400),
        (CustosClientError("down", 500), 503),
        (CustosServerError("down", 500), 503),
        (CustosError("boom"), 500),
    ],
)
async def test_authorize_maps_custos_errors(error, status_code):
    async def resolve_domain(_request):
        return "domain"

    settings = SimpleNamespace(
        custos_api_url="https://custos.example.com",
        authorization_cache_enabled=False,
        authorization_cache_ttl=300,
    )
    request = _make_request(
        user=SimpleNamespace(id="user-1"),
        headers={"Authorization": "Bearer token"},
    )

    with (
        patch(
            "tessera_sdk.utils.authorization_dependency.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency.CustosClient.authorize",
            side_effect=error,
        ),
    ):
        dependency = authorize("read", "resource", resolve_domain)

        with pytest.raises(HTTPException) as exc:
            await dependency(request)

    assert exc.value.status_code == status_code


def test_get_authorization_cache_disabled():
    authorization_dependency._authorization_cache = None
    settings = SimpleNamespace(authorization_cache_enabled=False)

    with patch(
        "tessera_sdk.utils.authorization_dependency.get_settings",
        return_value=settings,
    ):
        assert authorization_dependency._get_authorization_cache() is None


def test_get_authorization_cache_enabled_creates_cache():
    authorization_dependency._authorization_cache = None
    settings = SimpleNamespace(authorization_cache_enabled=True)
    cache_instance = Mock()

    with (
        patch(
            "tessera_sdk.utils.authorization_dependency.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.utils.authorization_dependency.Cache",
            return_value=cache_instance,
        ),
    ):
        assert authorization_dependency._get_authorization_cache() is cache_instance
