"""
Endpoint for bot restriction related endpoints
"""

from typing import Optional

from blacksheep.server.controllers import Controller, post
from blacksheep import FromJSON
from bot_models import RobloxUser, MemberSerializable
from hikari import Member
from attrs import define
from dataclasses import dataclass


@define()
class RestrictionPayload:
    roblox_user: RobloxUser = None
    member: MemberSerializable = None

    def __attrs_post_init__(self):
        self.roblox_user = RobloxUser(**self.roblox_user) if self.roblox_user else None
        self.member = MemberSerializable(**self.member) if self.member else None


class BindsController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/restrictions"

    @classmethod
    def class_name(cls) -> str:
        return "Restrictions"

    @post("/evaluate/:guild_id/:user_id")
    async def evaluate_restrictions(self, guild_id: int, user_id: int, input: FromJSON[RestrictionPayload]):
        """
        Calculates the restrictions for the user, if any.
        """

        data = input.value

        print(data)
