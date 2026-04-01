from pydantic import BaseModel


class OAuthTokenResponse(BaseModel):
    """Response for POST /oauth/token (client_credentials)."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
