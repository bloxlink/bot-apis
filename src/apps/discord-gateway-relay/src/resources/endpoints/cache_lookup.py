from discord import Guild, Member, User

from resources.ipc import RelayEndpoint, RelayRequest
from resources.modules.discord import client
from resources.utils import MinimalConversions, filter_dict

import logging

logger = logging.getLogger("CACHE_LOOKUP")


class CacheLookupEndpoint(RelayEndpoint):
    def __init__(self):
        super().__init__("CACHE_LOOKUP")

    async def handle(self, request: RelayRequest):
        query = request.payload["query"]
        query_data = request.payload["data"]
        query_fields = request.payload.get("fields", [])

        if "guild" in query:
            guild_id: int = query_data.get("guild_id")
            method: str = query.split(".")[1]

            # Retrieve the guild.
            guild: Guild | None = client.get_guild(guild_id)
            if not guild:
                logger.info(f"Ignored request, guild {guild_id} does not belong to target shard.")
                # Guild does not exist in node/shards, a different node should give a response.
                return

            if method == "data":
                await request.respond(MinimalConversions.convert(guild, query_fields))
                return

            elif method == "channels":
                result = []
                # channels = guild.channels

                for category, channels in guild.by_category():
                    if category:
                        result.append(MinimalConversions.convert_channel(category))
                    if channels:
                        for x in channels:
                            result.append(MinimalConversions.convert_channel(x))

                # TODO: Support channel_id list in data field.
                # channels = [MinimalConversions.convert(x, query_fields) for x in channels]
                await request.respond(result)

                return

            elif method == "roles":
                roles = guild.roles

                # TODO: Support role_id list in data field.
                roles = [filter_dict(MinimalConversions.convert_role(x), *query_fields) for x in roles]
                await request.respond(roles)

                return

            elif method == "member":
                member_id: int = int(query_data.get("user_id"))
                member: Member | None = guild.get_member(member_id)

                if member:
                    await request.respond(MinimalConversions.convert_member(member))
                return

            else:
                logger.error(
                    f"Query of {query} was not handled because it is not implemented."
                    " Double check that the right spelling was used when sending the query."
                )

        elif query == "user":
            user_id: int = int(request.payload["data"].get("user_id"))
            user: User | None = client.get_user(user_id)

            if user:
                requested_data = filter_dict(MinimalConversions.convert_user(user), *query_fields)
                await request.respond(requested_data)
            else:
                return
        else:
            logger.error(f"Query of {query} was not handled because it is not implemented.")
