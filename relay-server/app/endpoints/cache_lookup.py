from typing import Literal
from pydantic import Field
from discord import ChannelType, TextChannel
from bloxlink_lib import BaseModel
from ..base import RelayEndpoint
from ..types import Response
from ..redis import RedisRelayRequest
from ..bloxlink import bloxlink


class GuildData(BaseModel):
    """Data about a guild."""

    id: int
    name: str
    icon: str | None
    owner: int
    splash: str | None
    totalMembers: int
    createdDate: int


class RoleData(BaseModel):
    """Data about a role."""

    id: int
    name: str
    color: str
    hoist: bool
    position: int
    permissions: int
    managed: bool

class ChannelData(BaseModel):
    """Data about a channel."""

    id: int
    name: str
    position: int
    type: Literal[ChannelType.category, ChannelType.text]

class EndpointResponse(Response):
    """Response from the cache lookup endpoint."""

    result: GuildData | list[RoleData] | list[ChannelData]


class Payload(BaseModel):
    guild_id: int = Field(alias="guildID")
    type: Literal["channels", "roles", "guild"]


class CacheLookupEndpoint(RelayEndpoint[Payload]):
    """An endpoint for getting information from the cache."""

    def __init__(self):
        super().__init__("CACHE_LOOKUP", Payload)

    async def handle(self, request: RedisRelayRequest[Payload]) -> Response:
        payload = request.payload
        guild_id = payload.guild_id

        guild = bloxlink.get_guild(guild_id)

        if not guild:
            return

        match payload.type:
            case "guild":
                return Response(
                    success=True,
                    nonce=request.nonce,
                    result=GuildData(
                        id=guild.id,
                        name=guild.name,
                        icon=guild.icon,
                        owner=guild.owner_id,
                        splash=guild.splash,
                        totalMembers=len(guild.members),
                        createdDate=guild.created_at.timestamp()
                    )
                )
            case "roles":
                return Response(
                    success=True,
                    nonce=request.nonce,
                    result=[RoleData(
                        id=role.id,
                        name=role.name,
                        color=str(role.color),
                        hoist=role.hoist,
                        position=role.position,
                        permissions=role.permissions.value,
                        managed=role.managed
                    ) for role in guild.roles]
                )
            case "channels":
                channel_result: list[ChannelData] = []

                for category, channels in guild.by_category():
                    if category:
                        channel_result.append(ChannelData(
                            id=category.id,
                            name=category.name,
                            position=category.position,
                            type=ChannelType.category
                        ))

                    for channel in channels:
                        if isinstance(channel, TextChannel):
                            channel_result.append(ChannelData(
                                id=channel.id,
                                name=channel.name,
                                position=channel.position,
                                type=ChannelType.text
                            ))

                return Response(
                    success=True,
                    nonce=request.nonce,
                    result=channel_result
                )
            case _:
                return Response(success=False, nonce=request.nonce)
