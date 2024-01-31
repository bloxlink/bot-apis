"""
Endpoint for bot restriction related endpoints
"""

from typing import Optional

from blacksheep.server.controllers import Controller, post
from blacksheep import FromJSON
from bloxlink_lib import RobloxUser, MemberSerializable
from attrs import define
from ..models import Response
from ..lib.restrictions import calculate_restrictions


@define()
class RestrictionPayload:
    roblox_user: RobloxUser = None
    member: MemberSerializable = None

    def __attrs_post_init__(self):
        # blacksheep isn't casting the nested fields to the correct types

        self.roblox_user = RobloxUser(**self.roblox_user) if self.roblox_user else None
        self.member = MemberSerializable(**self.member) if self.member else None


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
