"""Per-call bearer tokens never leak into the shared client session."""

from unittest.mock import Mock

from tessera_sdk.clients.identies import IdentiesClient


def _client_with_response(payload):
    client = IdentiesClient(base_url="https://identies.example.com")
    response = Mock(status_code=200)
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    client.session.request = Mock(return_value=response)
    return client


def test_introspect_sends_bearer_for_this_call_only():
    client = _client_with_response({"active": False})

    client.introspect(bearer_token="ak_secret")

    headers = client.session.request.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer ak_secret"
    assert "Authorization" not in client.session.headers


def test_userinfo_sends_bearer_for_this_call_only():
    client = _client_with_response(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "email": "a@example.com",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    )

    client.userinfo(bearer_token="jwt-token")

    headers = client.session.request.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer jwt-token"
    assert "Authorization" not in client.session.headers
