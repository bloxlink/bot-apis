from typing import Annotated, Any
from pydantic import Field
from bloxlink_lib import BaseModel


class Response(BaseModel):
    """A response from each node."""

    nonce: str | None
    result: Any
    success: bool = None
    error: str | None = None


class PremiumResponse(BaseModel):
    """Response from the premium guild check bot endpoint."""

    premium: bool = False
    features: Annotated[list, Field(default_factory=list)]
