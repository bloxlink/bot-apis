"""
Endpoint for bind related endpoints
"""
from typing import Optional

from blacksheep.server.controllers import Controller, post
from blacksheep import FromJSON
from bot_utils import RobloxUser
from hikari import Member, Role
from attrs import define


@define()
class UpdateUserPayload:
    roles: dict[int, Role]
    roblox_user: RobloxUser
    member: Member


class BindsController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/binds"

    @classmethod
    def class_name(cls) -> str:
        return "Bind Endpoints"

    @post("/:guild_id/:user_id")
    async def update_user(self, guild_id: int, user_id: int, request: FromJSON[UpdateUserPayload]):
        """
        Calculates the bound roles and nickname for the user.
        """
        data = request.value
