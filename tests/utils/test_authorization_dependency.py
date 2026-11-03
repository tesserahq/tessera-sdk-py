from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from tessera_sdk.clients._base.exceptions import (
    TesseraAuthenticationError,
    TesseraClientError,
    TesseraError,
    TesseraServerError,
    TesseraValidationError,
)
from tessera_sdk.server.dependencies import authorization as authorization_dependency
from tessera_sdk.server.dependencies.authorization import authorize


class DummyAuthorizeResponse:
    def __init__(self, allowed: bool):
        self.allowed = allowed


def _make_request(user=None, headers=None, url_path="/"):
    if headers is None:
        headers = {}
    return SimpleNamespace(
        headers=headers,
        state=SimpleNamespace(user=user),
        url=SimpleNamespace(path=url_path),
    )


@pytest.mark.anyio
async def test_authorize_requires_auth_header():
    async def resolve_domain(_request):
        return "domain"

    dependency = authorize("read", "resource", resolve_domain)
    request = _make_request(user=SimpleNamespace(id="user-1"))

    with pytest.raises(HTTPException) as exc:
        await dependency(request)

    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_authorize_requires_user():
    async def resolve_domain(_request):
        return "domain"

    dependency = authorize("read", "resource", resolve_domain)
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
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.CustosClient.authorize",
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
        "tessera_sdk.server.dependencies.authorization.get_settings",
        return_value=settings,
    ):
        dependency = authorize("read", "resource", resolve_domain)

        with pytest.raises(ValueError, match="boom"):
            await dependency(request)


@pytest.mark.anyio
async def test_authorize_cache_hit_allows():
    async def resolve_domain(_request):
        return "domain"

    cache = Mock()
    cache.read.return_value = {"allowed": True}
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
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization._get_authorization_cache",
            return_value=cache,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.CustosClient.authorize",
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
    cache.read.return_value = {"allowed": False}
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
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization._get_authorization_cache",
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
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization._get_authorization_cache",
            return_value=cache,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.CustosClient.authorize",
            return_value=DummyAuthorizeResponse(False),
        ),
    ):
        dependency = authorize("read", "resource", resolve_domain)

        with pytest.raises(HTTPException) as exc:
            await dependency(request)

    cache.write.assert_called_once_with(
        "user-1:read:resource:domain", {"allowed": False}, ttl=300
    )
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
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization._get_authorization_cache",
            return_value=cache,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.CustosClient.authorize",
            return_value=DummyAuthorizeResponse(True),
        ),
    ):
        dependency = authorize("read", "resource", resolve_domain)
        result = await dependency(request)

    cache.write.assert_called_once_with(
        "user-1:read:resource:domain", {"allowed": True}, ttl=300
    )
    assert result is True


class _DictCache:
    def __init__(self):
        self.entries = {}

    def read(self, key):
        return self.entries.get(key)

    def write(self, key, value, ttl=None):
        self.entries[key] = value


@pytest.mark.anyio
@pytest.mark.parametrize("allowed", [True, False])
async def test_authorize_cached_decision_matches_custos(allowed):
    """A decision read back from the cache must match the one Custos gave."""

    async def resolve_domain(_request):
        return "domain"

    cache = _DictCache()
    settings = SimpleNamespace(
        custos_api_url="https://custos.example.com",
        authorization_cache_enabled=True,
        authorization_cache_ttl=300,
    )
    request = _make_request(
        user=SimpleNamespace(id="user-1"),
        headers={"Authorization": "Bearer token"},
    )

    async def call(dependency):
        try:
            return await dependency(request)
        except HTTPException as exc:
            return exc.status_code

    with (
        patch(
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization._get_authorization_cache",
            return_value=cache,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.CustosClient.authorize",
            return_value=DummyAuthorizeResponse(allowed),
        ) as mock_authorize,
    ):
        dependency = authorize("read", "resource", resolve_domain)
        first = await call(dependency)
        second = await call(dependency)

    mock_authorize.assert_called_once()
    expected = True if allowed else 403
    assert first == expected
    assert second == expected


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error, status_code",
    [
        (TesseraAuthenticationError("nope"), 401),
        (TesseraValidationError("bad"), 400),
        (TesseraClientError("down", 500), 503),
        (TesseraServerError("down", 500), 503),
        (TesseraError("boom"), 500),
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
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.CustosClient.authorize",
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
        "tessera_sdk.server.dependencies.authorization.get_settings",
        return_value=settings,
    ):
        assert authorization_dependency._get_authorization_cache() is None


def test_get_authorization_cache_enabled_creates_cache():
    authorization_dependency._authorization_cache = None
    settings = SimpleNamespace(authorization_cache_enabled=True)
    cache_instance = Mock()

    with (
        patch(
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=settings,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.Cache",
            return_value=cache_instance,
        ),
    ):
        assert authorization_dependency._get_authorization_cache() is cache_instance


_CUSTOS_SETTINGS = SimpleNamespace(
    custos_api_url="https://custos.example.com",
    authorization_cache_enabled=False,
    authorization_cache_ttl=300,
)


def test_authorize_requires_exactly_one_domain_source():
    with pytest.raises(ValueError):
        authorize("read", "resource")

    with pytest.raises(ValueError):
        authorize(
            "read",
            "resource",
            lambda _request: "d",
            domain_dependency=lambda: "d",
        )


@pytest.mark.anyio
async def test_authorize_runs_sync_resolver_off_the_event_loop():
    import threading

    loop_thread = threading.get_ident()
    seen = {}

    def resolve_domain(_request):
        seen["thread"] = threading.get_ident()
        return "domain-1"

    request = _make_request(
        user=SimpleNamespace(id="user-1"), headers={"Authorization": "Bearer t"}
    )
    custos = Mock()
    custos.authorize.return_value = DummyAuthorizeResponse(True)
    custos.session.headers = {}

    with (
        patch(
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=_CUSTOS_SETTINGS,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.CustosClient",
            return_value=custos,
        ),
    ):
        assert await authorize("read", "thing", resolve_domain)(request) is True

    assert seen["thread"] != loop_thread
    assert custos.authorize.call_args.kwargs["domain"] == "domain-1"


@pytest.mark.anyio
async def test_authorize_awaits_awaitable_from_plain_callable():
    async def resolve(_request):
        return "domain-2"

    request = _make_request(
        user=SimpleNamespace(id="user-1"), headers={"Authorization": "Bearer t"}
    )
    custos = Mock()
    custos.authorize.return_value = DummyAuthorizeResponse(True)
    custos.session.headers = {}

    with (
        patch(
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=_CUSTOS_SETTINGS,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.CustosClient",
            return_value=custos,
        ),
    ):
        dependency = authorize("read", "thing", lambda request: resolve(request))
        assert await dependency(request) is True

    assert custos.authorize.call_args.kwargs["domain"] == "domain-2"


def test_authorize_domain_dependency_shares_route_dependencies():
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    loads = []

    def get_thing(thing_id: str):
        loads.append(thing_id)
        return SimpleNamespace(id=thing_id, account_id="account-9")

    def thing_domain(thing=Depends(get_thing)) -> str:
        return thing.account_id

    app = FastAPI()

    @app.middleware("http")
    async def set_user(request, call_next):
        request.state.user = SimpleNamespace(id="user-1")
        return await call_next(request)

    @app.get("/things/{thing_id}")
    def read_thing(
        thing=Depends(get_thing),
        _authorized=Depends(authorize("read", "thing", domain_dependency=thing_domain)),
    ):
        return {"id": thing.id}

    custos = Mock()
    custos.authorize.return_value = DummyAuthorizeResponse(True)
    custos.session.headers = {}

    with (
        patch(
            "tessera_sdk.server.dependencies.authorization.get_settings",
            return_value=_CUSTOS_SETTINGS,
        ),
        patch(
            "tessera_sdk.server.dependencies.authorization.CustosClient",
            return_value=custos,
        ),
    ):
        response = TestClient(app).get(
            "/things/t-1", headers={"Authorization": "Bearer t"}
        )

    assert response.status_code == 200
    # FastAPI caches get_thing per request: authorization adds no extra load.
    assert loads == ["t-1"]
    assert custos.authorize.call_args.kwargs["domain"] == "account-9"
