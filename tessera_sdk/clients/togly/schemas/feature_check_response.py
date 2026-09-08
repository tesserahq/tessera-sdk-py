"""Response from the Togly single-feature check endpoint."""

from pydantic import BaseModel


class FeatureCheckResponse(BaseModel):
    """A feature decision returned by Togly."""

    key: str
    enabled: bool
