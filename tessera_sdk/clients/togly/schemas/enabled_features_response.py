"""Response from the Togly enabled-features endpoint."""

from pydantic import BaseModel


class EnabledFeaturesResponse(BaseModel):
    """Feature keys enabled for the requested actor or global context."""

    features: list[str]
