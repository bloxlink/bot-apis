"""
Endpoint for bot restriction related endpoints
"""

from typing import Optional

from blacksheep.server.controllers import Controller, post
from blacksheep import FromJSON
from bloxlink_lib import RobloxUser, BaseModel
from ..lib.restrictions import calculate_restrictions, RestrictedData


class RestrictionPayload(BaseModel):
    roblox_user: RobloxUser | None = None

class RestrictionResponse(RestrictedData):
    success: bool = True


class BindsController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/restrictions"

    @classmethod
    def class_name(cls) -> str:
        return "Restrictions"

    @post("/evaluate/:guild_id")
    async def evaluate_restrictions(self, guild_id: int, input: FromJSON[RestrictionPayload]) -> RestrictionResponse:
        """
        Calculates the restrictions for the user, if any.
        """

        data = input.value
        roblox_user = data.roblox_user

        restrict_data = await calculate_restrictions(guild_id=guild_id, roblox_user=roblox_user)

        return RestrictionResponse(
            success=True,
            **restrict_data.model_dump()
        )
