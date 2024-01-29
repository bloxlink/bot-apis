"""
Endpoint for bind related endpoints
"""
from typing import Optional

from blacksheep.server.controllers import Controller, post
from blacksheep import FromJSON
from bot_utils import RobloxUser, MemberSerializable
from hikari import Member, Role
from attrs import define
from ..models import Response


@define()
class UpdateUserPayload:
    roles: dict[int, Role]
    roblox_user: RobloxUser
    member: Member

    def __attrs_post_init__(self):
        # blacksheep isn't casting the nested fields to the correct types

        self.roblox_user = RobloxUser(**self.roblox_user) if self.roblox_user else None
        self.member = MemberSerializable(**self.member) if self.member else None


class BindCalculationResponse(Response):
    nickname: str | None

    finalRoles: list[str]
    addedRoles: list[str]
    removedRoles: list[str]
    missingRoles: list[str]


class BindsController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/binds"

    @classmethod
    def class_name(cls) -> str:
        return "Bind Endpoints"

    @post("/:guild_id/:user_id")
    async def calculate_binds_for_user(self, guild_id: int, user_id: int, input: FromJSON[UpdateUserPayload]) -> BindCalculationResponse:
        """
        Calculates the restrictions for the user, if any.
        """

        data = input.value
        roblox_user = data.roblox_user
        member = data.member
        roles = data.roles

        # # Call get_binds so we can get the converted bind format (if those weren't converted prior.)
        # # guild_data.binds = await get_binds(guild_id)

        # restrict_data = await calculate_restrictions(guild_id=guild_id, roblox_user=roblox_user)

        return BindCalculationResponse(
            success=True,
            nickname="ok",
            finalRoles=[],
            addedRoles=[],
            removedRoles=[],
            missingRoles=[]
        )
