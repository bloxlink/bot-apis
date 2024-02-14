"""
Endpoint for bot restriction related endpoints
"""

from typing import Optional

from blacksheep.server.controllers import Controller, post
from blacksheep import FromJSON
from bloxlink_lib import RobloxUser, MemberSerializable, BaseModel
from pydantic import Field
from ..models import Response
from ..lib.restrictions import calculate_restrictions


class RestrictionPayload(BaseModel):
    roblox_user: RobloxUser | None = Field(default=None)
    member: MemberSerializable


class RestrictionResponse(Response):
    restrict: bool
    reason: str


class BindsController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/restrictions"

    @classmethod
    def class_name(cls) -> str:
        return "Restrictions"

    @post("/evaluate/:guild_id/:user_id")
    async def evaluate_restrictions(self, guild_id: int, user_id: int, input: FromJSON[RestrictionPayload]) -> RestrictionResponse:
        """
        Calculates the restrictions for the user, if any.
        """

        data = input.value
        roblox_user = data.roblox_user
        member = data.member

        # Call get_binds so we can get the converted bind format (if those weren't converted prior.)
        # guild_data.binds = await get_binds(guild_id)

        restrict_data = await calculate_restrictions(guild_id=guild_id, roblox_user=roblox_user)

        return RestrictionResponse(
            success=True,
            **restrict_data
        )
