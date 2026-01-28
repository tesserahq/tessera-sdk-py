from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from tessera_sdk.identies.schemas.user_response import UserResponse
from tessera_sdk.middleware.user_onboarding import UserOnboardingMiddleware
from tessera_sdk.schemas.user import UserNeedsOnboarding


class SetUserMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, user):
        super().__init__(app)
        self.user = user

    async def dispatch(self, request, call_next):
        request.state.user = self.user
        return await call_next(request)


def _build_app(
    user,
    user_service_factory=None,
    skip_onboarding_paths=None,
):
    async def handler(request):
        user_state = getattr(request.state, "user", None)
        user_id = None
        if isinstance(user_state, dict):
            user_id = user_state.get("id")
        elif hasattr(user_state, "id"):
            user_id = str(user_state.id)
        return JSONResponse({"user_id": user_id})

    app = Starlette(routes=[Route("/protected", handler), Route("/skip", handler)])
    app.add_middleware(
        UserOnboardingMiddleware,
        user_service_factory=user_service_factory,
        skip_onboarding_paths=skip_onboarding_paths,
    )
    if user is not None:
        app.add_middleware(SetUserMiddleware, user=user)
    return app


def test_onboarding_skips_without_user():
    app = _build_app(user=None)
    client = TestClient(app)

    with patch(
        "tessera_sdk.middleware.user_onboarding.get_settings",
        return_value=SimpleNamespace(identies_api_url="https://identies.example.com"),
    ):
        response = client.get("/protected")

    assert response.status_code == 200
    assert response.json() == {"user_id": None}


def test_onboarding_passes_existing_user():
    existing_user = SimpleNamespace(id="user-1", needs_onboarding=False)
    app = _build_app(user=existing_user)
    client = TestClient(app)

    with patch(
        "tessera_sdk.middleware.user_onboarding.get_settings",
        return_value=SimpleNamespace(identies_api_url="https://identies.example.com"),
    ):
        response = client.get("/protected")

    assert response.status_code == 200
    assert response.json() == {"user_id": "user-1"}


def test_onboarding_creates_user_when_needed():
    external_id = "ext-1"
    onboarding_user = UserNeedsOnboarding(
        needs_onboarding=True, external_id=external_id
    )

    class DummyUserService:
        def onboard_user(self, user_data):
            return {"id": "local-1"}

    def user_service_factory():
        return DummyUserService()

    timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    userinfo = UserResponse(
        id=uuid4(),
        email="user@example.com",
        first_name="Ada",
        last_name="Lovelace",
        created_at=timestamp,
        updated_at=timestamp,
    )

    app = _build_app(user=onboarding_user, user_service_factory=user_service_factory)
    client = TestClient(app)

    with (
        patch(
            "tessera_sdk.middleware.user_onboarding.get_settings",
            return_value=SimpleNamespace(
                identies_api_url="https://identies.example.com"
            ),
        ),
        patch(
            "tessera_sdk.middleware.user_onboarding.IdentiesClient.userinfo",
            return_value=userinfo,
        ),
    ):
        response = client.get("/protected", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json() == {"user_id": "local-1"}


def test_onboarding_returns_error_when_onboard_fails():
    onboarding_user = UserNeedsOnboarding(needs_onboarding=True, external_id="ext-2")
    timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    userinfo = UserResponse(
        id=uuid4(),
        email="user@example.com",
        first_name="Ada",
        last_name="Lovelace",
        created_at=timestamp,
        updated_at=timestamp,
    )

    app = _build_app(user=onboarding_user, user_service_factory=None)
    client = TestClient(app)

    with (
        patch(
            "tessera_sdk.middleware.user_onboarding.get_settings",
            return_value=SimpleNamespace(
                identies_api_url="https://identies.example.com"
            ),
        ),
        patch(
            "tessera_sdk.middleware.user_onboarding.IdentiesClient.userinfo",
            return_value=userinfo,
        ),
    ):
        response = client.get("/protected", headers={"Authorization": "Bearer token"})

    assert response.status_code == 500
    assert response.json() == {
        "detail": "User onboarding failed. Please contact support if this issue persists."
    }


def test_onboarding_can_be_skipped_for_paths():
    onboarding_user = UserNeedsOnboarding(needs_onboarding=True, external_id="ext-skip")
    app = _build_app(user=onboarding_user, skip_onboarding_paths=["/skip"])
    client = TestClient(app)

    with (
        patch(
            "tessera_sdk.middleware.user_onboarding.get_settings",
            return_value=SimpleNamespace(
                identies_api_url="https://identies.example.com"
            ),
        ),
        patch(
            "tessera_sdk.middleware.user_onboarding.IdentiesClient.userinfo"
        ) as userinfo_mock,
    ):
        response = client.get("/skip", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    # UserNeedsOnboarding has no `id`, and we skipped onboarding, so handler returns None
    assert response.json() == {"user_id": None}
    userinfo_mock.assert_not_called()
