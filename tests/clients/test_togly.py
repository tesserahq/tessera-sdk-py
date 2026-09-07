from unittest.mock import Mock, patch

import pytest

from tessera_sdk import ToglyClient
from tessera_sdk.clients._base.exceptions import (
    TesseraAuthenticationError,
    TesseraClientError,
    TesseraError,
    TesseraServerError,
)
from tessera_sdk.constants import HTTPMethods


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_is_enabled_checks_actor_and_parses_response():
    client = ToglyClient(
        base_url="https://togly.example.com",
        api_token="token",
    )

    with patch.object(
        client,
        "_make_request",
        return_value=DummyResponse({"key": "new-dashboard", "enabled": True}),
    ) as request:
        enabled = client.is_enabled("new-dashboard", actor_id="project-1")

    assert enabled is True
    request.assert_called_once_with(
        HTTPMethods.GET,
        "/feature-checks/new-dashboard",
        params={"actor_id": "project-1"},
        headers=None,
    )


def test_is_enabled_supports_global_checks_and_url_encodes_key():
    client = ToglyClient(
        base_url="https://togly.example.com",
        api_token="token",
    )

    with patch.object(
        client,
        "_make_request",
        return_value=DummyResponse({"key": "release/preview", "enabled": False}),
    ) as request:
        enabled = client.is_enabled("release/preview")

    assert enabled is False
    request.assert_called_once_with(
        HTTPMethods.GET,
        "/feature-checks/release%2Fpreview",
        params=None,
        headers=None,
    )


def test_enabled_features_returns_enabled_keys_only():
    client = ToglyClient(
        base_url="https://togly.example.com",
        api_token="token",
    )

    with patch.object(
        client,
        "_make_request",
        return_value=DummyResponse({"features": ["one", "two"]}),
    ) as request:
        features = client.enabled_features(actor_id="project-1")

    assert features == ["one", "two"]
    request.assert_called_once_with(
        HTTPMethods.GET,
        "/enabled-features",
        params={"actor_id": "project-1"},
        headers=None,
    )


def test_auth_token_provider_supplies_each_request_token():
    provider = Mock()
    provider.get_token.return_value = "fresh-token"
    client = ToglyClient(
        base_url="https://togly.example.com",
        auth_token_provider=provider,
    )

    with patch.object(
        client,
        "_make_request",
        return_value=DummyResponse({"key": "flag", "enabled": True}),
    ) as request:
        client.is_enabled("flag")

    provider.get_token.assert_called_once_with()
    request.assert_called_once_with(
        HTTPMethods.GET,
        "/feature-checks/flag",
        params=None,
        headers={"Authorization": "Bearer fresh-token"},
    )


@pytest.mark.parametrize(
    "error",
    [
        TesseraError("network unavailable"),
        TesseraServerError("togly unavailable", status_code=503),
    ],
)
def test_is_enabled_returns_default_for_transport_and_server_errors(error):
    client = ToglyClient(
        base_url="https://togly.example.com",
        api_token="token",
    )

    with patch.object(client, "_make_request", side_effect=error):
        assert client.is_enabled("flag", default=True) is True


def test_enabled_features_returns_a_copy_of_fallback():
    client = ToglyClient(
        base_url="https://togly.example.com",
        api_token="token",
    )
    default = ["safe-feature"]

    with patch.object(
        client,
        "_make_request",
        side_effect=TesseraServerError("unavailable", status_code=500),
    ):
        result = client.enabled_features(default=default)

    assert result == default
    assert result is not default


@pytest.mark.parametrize(
    "error",
    [
        TesseraAuthenticationError("unauthenticated"),
        TesseraClientError("forbidden", status_code=403),
        TesseraClientError("invalid actor", status_code=422),
    ],
)
def test_client_and_authentication_errors_remain_visible(error):
    client = ToglyClient(
        base_url="https://togly.example.com",
        api_token="token",
    )

    with patch.object(client, "_make_request", side_effect=error), pytest.raises(
        type(error)
    ):
        client.is_enabled("flag", default=True)


def test_invalid_success_payload_remains_visible():
    client = ToglyClient(
        base_url="https://togly.example.com",
        api_token="token",
    )

    with patch.object(
        client,
        "_make_request",
        return_value=DummyResponse({"enabled": "not-a-boolean"}),
    ), pytest.raises(TesseraClientError, match="invalid response payload"):
        client.is_enabled("flag")


def test_togly_client_uses_fractional_default_timeout():
    client = ToglyClient(
        base_url="https://togly.example.com",
        api_token="token",
    )

    assert client.timeout == pytest.approx(0.3)


def test_togly_client_rejects_ambiguous_authentication():
    with pytest.raises(ValueError, match="api_token or auth_token_provider"):
        ToglyClient(
            base_url="https://togly.example.com",
            api_token="token",
            auth_token_provider=Mock(),
        )
