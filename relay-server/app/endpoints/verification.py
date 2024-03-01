import logging
from bloxlink_lib import BaseModel, fetch, StatusCodes
from ..base import RelayEndpoint
from ..config import CONFIG
from ..redis import RedisRelayRequest
from ..bloxlink import bloxlink



class Payload(BaseModel):
    """Payload for the verification endpoint."""

    user_id: int
    guild_id: int


class Response(BaseModel):
    """Response from the verification endpoint."""

    success: bool


class VerificationEndpoint(RelayEndpoint[Payload]):
    """An endpoint for remotely updating a user.

    TODO: make this an endpoint on the http bot itself after MVP. This is on the relay server for compatibility with API.

    """

    def __init__(self):
        super().__init__("VERIFICATION", Payload)

    async def handle(self, request: RedisRelayRequest[Payload]) -> Response:
        payload = request.payload
        guild_id = payload.guild_id
        user_id = payload.user_id

        guild = bloxlink.get_guild(guild_id)

        if not guild:
            return

        text, response = await fetch(
            "POST",
            f"{CONFIG.HTTP_BOT_API}/api/update/user",
            headers={"Authorization": CONFIG.HTTP_BOT_AUTH},
            body={
                "guild_id": guild.id,
                "member_id": user_id
            },
            raise_on_failure=False
        )

        if response.status != StatusCodes.OK:
            logging.error(f"Verification endpoint response: {response.status}, {text}")


        return Response(success=response.status == StatusCodes.OK)
