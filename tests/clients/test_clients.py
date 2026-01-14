from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import patch

import pytest

from tessera_sdk.base.exceptions import (
    TesseraAuthenticationError,
    TesseraValidationError,
)
from tessera_sdk.constants import HTTPMethods
from tessera_sdk.custos import CustosClient
from tessera_sdk.custos.exceptions import CustosValidationError
from tessera_sdk.identies import IdentiesClient
from tessera_sdk.identies.exceptions import IdentiesAuthenticationError
from tessera_sdk.quore import QuoreClient
from tessera_sdk.quore.exceptions import QuoreValidationError
from tessera_sdk.sendly import SendlyClient
from tessera_sdk.sendly.schemas import SendEmailRequest
from tessera_sdk.vaulta import VaultaClient


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


def test_identies_maps_auth_errors():
    client = IdentiesClient(base_url="https://identies.example.com")

    with patch.object(
        IdentiesClient,
        "_make_request",
        side_effect=TesseraAuthenticationError("nope"),
    ):
        with pytest.raises(IdentiesAuthenticationError):
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
        with pytest.raises(QuoreValidationError):
            client.summarize(
                project_id="project-1",
                prompt_id="prompt-1",
                text="Long text",
                query="what happened",
            )


def test_sendly_send_email_uses_payload():
    request = SendEmailRequest(
        name="Welcome",
        tenant_id="tenant-1",
        from_email="noreply@example.com",
        subject="Welcome!",
        html="<p>Hello</p>",
        to=["user@example.com"],
        template_variables={"name": "Ada"},
    )
    payload = {
        "from_email": "noreply@example.com",
        "to_email": "user@example.com",
        "subject": "Welcome!",
        "body": "<p>Hello</p>",
        "status": "sent",
        "provider_id": "provider-1",
        "provider_message_id": "message-1",
        "tenant_id": "tenant-1",
        "id": "email-1",
    }
    client = SendlyClient(base_url="https://sendly.example.com")

    with patch.object(
        SendlyClient, "_make_request", return_value=DummyResponse(payload)
    ) as mock_request:
        result = client.send_email(request)

    mock_request.assert_called_once_with(
        HTTPMethods.POST,
        "/emails/send",
        data=request.model_dump(),
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
        with pytest.raises(CustosValidationError):
            client.authorize(
                user_id="user-1",
                action="read",
                resource="account",
                domain="account:1",
            )
