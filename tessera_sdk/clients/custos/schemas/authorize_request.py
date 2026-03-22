from pydantic import BaseModel


class AuthorizeRequest(BaseModel):
    """Schema for authorization request."""

    user_id: str
    """User identifier."""

    action: str
    """Action to authorize (e.g., 'create', 'read', 'update', 'delete')."""

    resource: str
    """Resource type to authorize (e.g., 'account', 'document')."""

    domain: str
    """Domain identifier (e.g., 'account:1234')."""

    model_config = {"from_attributes": True}
