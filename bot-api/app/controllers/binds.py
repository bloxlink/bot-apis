"""
Endpoint for bind related endpoints
"""

from typing import Optional

from blacksheep.server.controllers import Controller, post
from blacksheep import FromJSON
from bloxlink_lib import RobloxUser, MemberSerializable, RoleSerializable, BaseModel, parse_template, SnowflakeSet
from bloxlink_lib.database import fetch_guild_data
from ..models import Response
from ..lib.binds import filter_binds


class UpdateUserPayload(BaseModel):
    guild_roles: dict[int, RoleSerializable]
    guild_name: str
    roblox_user: RobloxUser | None
    member: MemberSerializable


class BindCalculationResponse(Response):
    nickname: str | None # nickname to set

    addRoles: list[int] # add these roles
    removeRoles: list[int] # remove these roles
    missingRoles: list[str] # missing roles, created by bot


class BindsController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/binds"

    @classmethod
    def class_name(cls) -> str:
        return "Bind Endpoints"

    @post("/:guild_id/:user_id")
    async def calculate_binds_for_user(self, guild_id: int, user_id: int, input: FromJSON[UpdateUserPayload]) -> BindCalculationResponse:
        """Calculates the binds for the user."""

        data = input.value
        roblox_user = data.roblox_user
        member = data.member
        guild_roles = data.guild_roles
        guild_name = data.guild_name

        bound_roles = BindCalculationResponse(
            success=True,
            nickname=None,
            addRoles=[],
            removeRoles=[],
            missingRoles=[]
        )

        guild_data = await fetch_guild_data(
            guild_id,
            "allowOldRoles",
        )

        potential_binds, remove_roles, missing_roles = await filter_binds(guild_id, roblox_user, member, guild_roles)
        nickname = await parse_template(
            guild_id=guild_id,
            guild_name=guild_name,
            potential_binds=potential_binds,
            member=member,
            roblox_user=roblox_user
        )

        if not guild_data.allowOldRoles:
            bound_roles["removeRoles"] = list(remove_roles)

        bound_roles["addRoles"] = list(SnowflakeSet([role_id for bind in potential_binds for role_id in bind.roles]))
        bound_roles["missingRoles"] = list(missing_roles)
        bound_roles["nickname"] = nickname

        print(bound_roles)

        return bound_roles
