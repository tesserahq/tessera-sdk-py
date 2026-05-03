from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import patch

import pytest

from tessera_sdk.clients._base.exceptions import (
    TesseraAuthenticationError,
    TesseraValidationError,
)
from tessera_sdk.constants import HTTPMethods
from tessera_sdk.clients.custos import CustosClient
from tessera_sdk.clients.identies import IdentiesClient
from tessera_sdk.clients.modela import ModelaClient
from tessera_sdk.clients.modela.schemas import CompletionMessage
from tessera_sdk.clients.quore import QuoreClient
from tessera_sdk.clients.sendly import SendlyClient
from tessera_sdk.clients.sendly.schemas import CreateEmailRequest
from tessera_sdk.clients.vaulta import VaultaClient


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_identies_userinfo_returns_user():
    user_id = uuid4()
    payload = {
        "id": str(user_id),
        "email": "user@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client = IdentiesClient(base_url="https://identies.example.com")

    with patch.object(
        IdentiesClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.userinfo()

    mock_request.assert_called_once_with(HTTPMethods.GET, "/userinfo")
    assert result.id == user_id
    assert result.email == "user@example.com"


def test_identies_introspect_uses_post():
    payload = {
        "active": True,
        "user_id": str(uuid4()),
        "expires_at": datetime.now(timezone.utc).isoformat(),
    }
    client = IdentiesClient(base_url="https://identies.example.com")

    with patch.object(
        IdentiesClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.introspect()

    mock_request.assert_called_once_with(HTTPMethods.POST, "/api-keys/introspect")
    assert result.active is True


def test_identies_get_token_posts_oauth_token():
    payload = {
        "access_token": "jwt-here",
        "token_type": "Bearer",
        "expires_in": 900,
    }
    client = IdentiesClient(base_url="https://identies.example.com")

    with patch.object(
        IdentiesClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.get_token(
            client_id="cid",
            client_secret="secret",
            audience="https://api.example.com",
        )

    mock_request.assert_called_once_with(
        HTTPMethods.POST,
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "cid",
            "client_secret": "secret",
            "audience": "https://api.example.com",
        },
    )
    assert result.access_token == "jwt-here"
    assert result.token_type == "Bearer"
    assert result.expires_in == 900


def test_identies_get_me_returns_current_user():
    user_id = uuid4()
    payload = {
        "id": str(user_id),
        "email": "me@example.com",
        "first_name": "Grace",
        "last_name": "Hopper",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client = IdentiesClient(base_url="https://identies.example.com")

    with patch.object(
        IdentiesClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.get_me()

    mock_request.assert_called_once_with(HTTPMethods.GET, "/me")
    assert result.id == user_id
    assert result.email == "me@example.com"


def test_identies_maps_auth_errors():
    client = IdentiesClient(base_url="https://identies.example.com")

    with patch.object(
        IdentiesClient,
        "_make_request",
        side_effect=TesseraAuthenticationError("nope"),
    ):
        with pytest.raises(TesseraAuthenticationError):
            client.userinfo()


def test_quore_summarize_builds_request():
    payload = {
        "summary": "Short summary",
        "prompt_id": "prompt-1",
        "labels": {"source": "doc"},
        "tokens_used": 12,
        "query": "what happened",
    }
    client = QuoreClient(base_url="https://quore.example.com")

    with patch.object(
        QuoreClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.summarize(
            project_id="project-1",
            prompt_id="prompt-1",
            text="Long text",
            query="what happened",
            labels={"source": "doc"},
        )

    mock_request.assert_called_once_with(
        HTTPMethods.POST,
        "/projects/project-1/summarize",
        data={
            "prompt_id": "prompt-1",
            "text": "Long text",
            "labels": {"source": "doc"},
            "query": "what happened",
        },
    )
    assert result.summary == "Short summary"


def test_quore_maps_validation_errors():
    client = QuoreClient(base_url="https://quore.example.com")

    with patch.object(
        QuoreClient,
        "_make_request",
        side_effect=TesseraValidationError("invalid"),
    ):
        with pytest.raises(TesseraValidationError):
            client.summarize(
                project_id="project-1",
                prompt_id="prompt-1",
                text="Long text",
                query="what happened",
            )


def test_sendly_create_email_uses_payload():
    request = CreateEmailRequest(
        project_id="7ffd064b-27c0-4a87-8065-46af46852db8",
        from_email="noreply@example.com",
        subject="Welcome!",
        html="<p>Hello ${name}!</p>",
        to=["user@example.com"],
        template_variables={"name": "Ada"},
    )
    payload = {
        "from_email": "noreply@example.com",
        "to_email": "user@example.com",
        "subject": "Welcome!",
        "body": "<p>Hello Ada!</p>",
        "status": "sent",
        "provider": "provider-1",
        "provider_message_id": "message-1",
        "project_id": "7ffd064b-27c0-4a87-8065-46af46852db8",
        "id": "email-1",
    }
    client = SendlyClient(base_url="https://sendly.example.com")

    with patch.object(
        SendlyClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.create_email(request)

    mock_request.assert_called_once_with(
        HTTPMethods.POST,
        "/emails",
        data=request.model_dump(mode="json"),
    )
    assert result.status == "sent"


def test_vaulta_get_asset_returns_response():
    payload = {
        "id": "asset-1",
        "name": "Report",
        "filename": "report.pdf",
        "mime_type": "application/pdf",
        "size": 1024,
        "labels": {"type": "report"},
        "state": "completed",
    }
    client = VaultaClient(base_url="https://vaulta.example.com")

    with patch.object(
        VaultaClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.get_asset("asset-1")

    mock_request.assert_called_once_with(HTTPMethods.GET, "/assets/asset-1")
    assert result.id == "asset-1"


def test_custos_authorize_posts_request():
    payload = {
        "allowed": True,
        "user_id": "user-1",
        "action": "read",
        "resource": "account",
        "domain": "account:1",
    }
    client = CustosClient(base_url="https://custos.example.com")

    with patch.object(
        CustosClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.authorize(
            user_id="user-1",
            action="read",
            resource="account",
            domain="account:1",
        )

    mock_request.assert_called_once_with(
        HTTPMethods.POST,
        "/authorization/authorize",
        data={
            "user_id": "user-1",
            "action": "read",
            "resource": "account",
            "domain": "account:1",
        },
    )
    assert result.allowed is True


def test_custos_create_membership_posts_request():
    payload = {
        "membership_id": "membership-1",
        "role_id": "role-1",
        "user_id": "user-1",
        "domain": "account:1",
        "domain_metadata": {"tier": "gold"},
    }
    client = CustosClient(base_url="https://custos.example.com")

    with patch.object(
        CustosClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.create_membership(
            role_identifier="role-1",
            user_id="user-1",
            domain="account:1",
            domain_metadata={"tier": "gold"},
        )

    mock_request.assert_called_once_with(
        HTTPMethods.POST,
        "/roles/role-1/memberships",
        data={
            "user_id": "user-1",
            "domain": "account:1",
            "domain_metadata": {"tier": "gold"},
        },
    )
    assert result.membership_id == "membership-1"


def test_custos_delete_membership_uses_delete():
    client = CustosClient(base_url="https://custos.example.com")

    with patch.object(
        CustosClient, "_make_request", return_value=DummyResponse({})
    ) as mock_request:
        client.delete_membership(
            role_identifier="role-1",
            user_id="user-1",
            domain="account:1",
        )

    mock_request.assert_called_once_with(
        HTTPMethods.DELETE,
        "/roles/role-1/memberships",
        data={
            "user_id": "user-1",
            "domain": "account:1",
        },
    )


def test_custos_maps_validation_errors():
    client = CustosClient(base_url="https://custos.example.com")

    with patch.object(
        CustosClient,
        "_make_request",
        side_effect=TesseraValidationError("invalid"),
    ):
        with pytest.raises(TesseraValidationError):
            client.authorize(
                user_id="user-1",
                action="read",
                resource="account",
                domain="account:1",
            )


# --- ModelaClient ---

FAKE_COMPLETION_RESPONSE = {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "openai-gpt-4o",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello!"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}


def test_modela_complete_posts_to_correct_endpoint():
    client = ModelaClient(base_url="https://modela.example.com")
    messages = [CompletionMessage(role="user", content="Hello")]

    with patch.object(
        ModelaClient,
        "_make_request",
        return_value=DummyResponse(FAKE_COMPLETION_RESPONSE),
    ) as mock_request:
        result = client.complete(messages=messages, model="openai-gpt-4o")

    mock_request.assert_called_once_with(
        HTTPMethods.POST,
        "/chat/completions",
        data={
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "openai-gpt-4o",
        },
        params={"project_id": "*"},
    )
    assert result.id == "chatcmpl-abc123"
    assert result.model == "openai-gpt-4o"
    assert result.choices[0].message.content == "Hello!"
    assert result.usage.total_tokens == 15


def test_modela_complete_omits_model_when_not_provided():
    client = ModelaClient(base_url="https://modela.example.com")
    messages = [CompletionMessage(role="user", content="Hi")]

    with patch.object(
        ModelaClient,
        "_make_request",
        return_value=DummyResponse(FAKE_COMPLETION_RESPONSE),
    ) as mock_request:
        client.complete(messages=messages)

    call_data = mock_request.call_args.kwargs["data"]
    assert "model" not in call_data


def test_modela_complete_passes_project_id_as_query_param():
    client = ModelaClient(base_url="https://modela.example.com")
    messages = [CompletionMessage(role="user", content="Hi")]

    with patch.object(
        ModelaClient,
        "_make_request",
        return_value=DummyResponse(FAKE_COMPLETION_RESPONSE),
    ) as mock_request:
        client.complete(messages=messages, project_id="proj-42")

    assert mock_request.call_args.kwargs["params"] == {"project_id": "proj-42"}


def test_modela_complete_raises_on_auth_error():
    client = ModelaClient(base_url="https://modela.example.com")
    messages = [CompletionMessage(role="user", content="Hi")]

    with patch.object(
        ModelaClient,
        "_make_request",
        side_effect=TesseraAuthenticationError("unauthorized"),
    ):
        with pytest.raises(TesseraAuthenticationError):
            client.complete(messages=messages)
