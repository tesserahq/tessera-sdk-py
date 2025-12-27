from pydantic import BaseModel


class CreateBindingRequest(BaseModel):
    """Schema for creating a role binding."""

    user_id: str
    """User identifier to bind to the role."""

    domain: str
    """Domain identifier for the binding."""

    class ConfigDict:
        """Pydantic model configuration."""

        from_attributes = True


class DeleteBindingRequest(BaseModel):
    """Schema for deleting a role binding."""

    user_id: str
    """User identifier to unbind from the role."""

    domain: str
    """Domain identifier for the binding."""

    class ConfigDict:
        """Pydantic model configuration."""

        from_attributes = True
