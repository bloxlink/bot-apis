"""
Endpoint for bind related endpoints
"""

from typing import Optional

from blacksheep.server.controllers import Controller, post
from blacksheep import FromJSON
from bloxlink_lib import RobloxUser, MemberSerializable, RoleSerializable, BaseModel
from bloxlink_lib.database import fetch_guild_data
from ..models import Response
from ..lib.binds import filter_binds


class UpdateUserPayload(BaseModel):
    guild_roles: dict[int, RoleSerializable]
    roblox_user: RobloxUser | None
    member: MemberSerializable

    # def __attrs_post_init__(self):
    #     # blacksheep isn't casting the nested fields to the correct types

    #     self.roblox_user = RobloxUser(**self.roblox_user) if self.roblox_user else None
    #     self.member = MemberSerializable(**self.member) if self.member else None
    #     self.roles = {role_id: RoleSerializable(**role) for role_id, role in self.roles.items()}


class BindCalculationResponse(Response):
    nickname: str | None # nickname to set

    finalRoles: list[str] # final roles the user will have
    addRoles: list[str] # add these roles
    removeRoles: list[str] # remove these roles
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

        bound_roles = BindCalculationResponse(
            success=True,
            nickname=None,
            finalRoles=[],
            addRoles=[],
            removeRoles=[],
            missingRoles=[]
        )

        guild_data = await fetch_guild_data(
            guild_id,
            "binds",
            "allowOldRoles",
            "verifiedRoleEnabled",
            "verifiedRoleName",
            "unverifiedRoleEnabled",
            "unverifiedRoleName",
            "ageLimit",
            "disallowAlts",
            "disallowBanEvaders",
            "groupLock",
        )

        potential_binds, remove_roles, missing_roles = await filter_binds(guild_data.binds, roblox_user, member, guild_roles)

        if not guild_data.allowOldRoles:
            bound_roles["removeRoles"] = remove_roles

        bound_roles["addRoles"] = [role_id for bind in potential_binds for role_id in bind.roles]
        bound_roles["missingRoles"] = missing_roles

        print("potential binds", potential_binds)
        print("remove roles", remove_roles)

        return bound_roles
