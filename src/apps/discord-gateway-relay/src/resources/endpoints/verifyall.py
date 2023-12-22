import asyncio
import logging
import math

from discord import Forbidden, Guild, HTTPException

from resources.ipc import RelayEndpoint, RelayRequest
from resources.modules.discord import client
from resources.modules.redis import redis_connection
from resources.secrets import BIND_API, BIND_API_AUTH
from resources.utils import MinimalConversions, ReturnType, fetch


class VerifyallEndpoint(RelayEndpoint):
    def __init__(self):
        super().__init__("VERIFYALL")

    async def handle(self, request: RelayRequest):
        payload = request.payload
        guild_id = payload.get("guild_id")
        channel_id = payload.get("channel_id")
        chunk_limit = payload.get("chunk_limit")

        logging.debug(f"/verifyall request received for {guild_id}")

        logging.debug(f"Getting guild {guild_id}")
        guild = client.get_guild(guild_id)
        try:
            if not guild:
                logging.debug(f"Fetching guild {guild_id}")
                guild = await client.fetch_guild(guild_id)
        except Forbidden:
            await request.respond(
                {
                    "status": "error",
                    "errors": f"I do not have access to the requested guild ({guild_id}).",
                }
            )
            return
        except HTTPException as ex:
            await request.respond(
                {
                    "status": "error",
                    "message": "An error was encountered retrieving the requested guild "
                    f"{guild_id} - (Status: {ex.status}, Code: {ex.code}, Text:{ex.text}).",
                }
            )
            return

        # Acknowledge a successful request.
        await request.respond({"status": "success"})

        # Needs to be done or the redis response will timeout (for some reason) and only the first
        # chunk will be sent.
        asyncio.create_task(self._handle_chunks(guild, channel_id, chunk_limit))

    async def _handle_chunks(self, guild: Guild, channel_id, chunk_limit):
        members = guild.members
        if not guild.chunked:
            logging.debug("Chunking the members of the guild.")
            members = await guild.chunk()

        cooldown_key = f"guild_scan:{guild.id}"
        await redis_connection.set(cooldown_key, "2", ex=86400)

        logging.debug(f"Splitting the chunked guild members into smaller chunks.")
        split_chunk = [members[i : i + chunk_limit] for i in range(0, len(members), chunk_limit)]

        for i, chunk in enumerate(split_chunk):
            is_final = i == len(split_chunk) - 1
            chunk = [MinimalConversions.convert_member(x) for x in chunk]

            logging.debug(f"Sending chunk {i + 1} of {len(split_chunk)} chunks.")
            text, response = await fetch(
                "POST",
                f"{BIND_API}/api/update/users",
                headers={"Authorization": BIND_API_AUTH},
                body={"guild_id": guild.id, "channel_id": channel_id, "members": chunk, "is_done": is_final},
                return_data=ReturnType.TEXT,
                timeout=None,
            )
            logging.debug(f"BOT SERVER RESPONSE: {response.status}, {text}")

            if response.status > 400:
                logging.error(f"BOT SERVER RESPONSE: {response.status}, {text}")
                break

            # Wait 3 seconds before sending the next request.
            logging.debug(f"Sleeping for 3 seconds.")
            await asyncio.sleep(3)

        # Once chunks are all sent (or an error stopped chunk sending), recalculate the cooldown.
        cooldown_1 = math.ceil((guild.member_count / 1000) * 120)
        cooldown_2 = 120
        cooldown = max(cooldown_1, cooldown_2)

        await redis_connection.set(cooldown_key, "3", ex=cooldown * 60)
