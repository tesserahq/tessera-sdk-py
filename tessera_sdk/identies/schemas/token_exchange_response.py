from pydantic import BaseModel


class TokenExchangeResponse(BaseModel):
    """Response for token exchange."""

    access_token: str
    token_type: str
    expires_in: int
    scope: str
