from types import SimpleNamespace
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from tessera_sdk.middleware.authentication import AuthenticationMiddleware


def _build_app():
    async def handler(request):
        user = getattr(request.state, "user", None)
        user_id = None
        if isinstance(user, dict):
            user_id = user.get("id")
        return JSONResponse({"user_id": user_id})

    app = Starlette(
        routes=[
            Route("/protected", handler),
            Route("/health", handler),
        ]
    )
    app.add_middleware(
        AuthenticationMiddleware,
        identies_base_url="https://identies.example.com",
    )
    return app


def test_auth_middleware_skips_paths():
    app = _build_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200


def test_auth_middleware_requires_token():
    app = _build_app()
    client = TestClient(app)

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.json() == {"error": "Missing or invalid token"}


def test_auth_middleware_allows_valid_bearer():
    app = _build_app()
    client = TestClient(app)

    def _set_user(request, token, user_service_factory=None):
        request.state.user = {"id": "user-1"}

    with patch(
        "tessera_sdk.middleware.authentication.verify_token_dependency",
        side_effect=_set_user,
    ):
        response = client.get("/protected", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json() == {"user_id": "user-1"}


def test_auth_middleware_rejects_invalid_bearer():
    app = _build_app()
    client = TestClient(app)

    with patch(
        "tessera_sdk.middleware.authentication.verify_token_dependency",
        side_effect=HTTPException(status_code=401, detail="Invalid"),
    ):
        response = client.get("/protected", headers={"Authorization": "Bearer token"})

    assert response.status_code == 401
    assert response.json() == {"error": "Invalid token"}


def test_auth_middleware_accepts_api_key():
    app = _build_app()
    client = TestClient(app)

    introspect = SimpleNamespace(active=True, user={"id": "user-2"}, user_id="user-2")

    with patch(
        "tessera_sdk.middleware.authentication.IdentiesClient.introspect",
        return_value=introspect,
    ):
        response = client.get("/protected", headers={"X-API-Key": "key-1"})

    assert response.status_code == 200
    assert response.json() == {"user_id": "user-2"}


def test_auth_middleware_rejects_inactive_api_key():
    app = _build_app()
    client = TestClient(app)

    introspect = SimpleNamespace(active=False, user=None, user_id=None)

    with patch(
        "tessera_sdk.middleware.authentication.IdentiesClient.introspect",
        return_value=introspect,
    ):
        response = client.get("/protected", headers={"X-API-Key": "key-1"})

    assert response.status_code == 401
    assert response.json() == {"error": "Invalid or inactive API key"}
