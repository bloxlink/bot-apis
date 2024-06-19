import json
import asyncio
import logging
from datetime import timedelta, datetime
from bloxlink_lib import parse_into, BaseModel, create_task_log_exception, StatusCodes, fetch, MemberSerializable
from bloxlink_lib.database import redis
import discord
from ..config import CONFIG
from ..base import RelayEndpoint
from ..redis import RedisRelayRequest
from ..bloxlink import bloxlink
from ..types import Response


class Payload(BaseModel):
    """Payload for verifyall endpoint"""

    guild_id: int
    channel_id: int
    chunk_limit: int

class VerifyAllProgress(BaseModel):
    """Progress of the /verifyall scan"""
    
    started_at: datetime
    ended_at: datetime | None = None
    members_processed: int
    total_members: int
    current_chunk: int
    total_chunks: int


async def record_progress(nonce: str, progress: int, total: int, current_chunk: int, total_chunks: int):
    """Record the progress of the verification."""

    current_progress: dict = json.loads(await redis.get(f"progress:{nonce}")) if await redis.exists(f"progress:{nonce}") else {}

    if not current_progress:
        current_progress = {
            "started_at": datetime.now(),
            "members_processed": progress,
            "total_members": total,
            "current_chunk": current_chunk,
            "total_chunks": total_chunks
        }

    parsed_progress = parse_into(current_progress, VerifyAllProgress)
    parsed_progress.members_processed = progress + parsed_progress.members_processed
    parsed_progress.current_chunk = current_chunk
    parsed_progress.total_chunks = total_chunks

    if total_chunks == current_chunk and total_chunks != 0:
        parsed_progress.ended_at = datetime.now()

    await redis.set(f"progress:{nonce}", parsed_progress, expire=timedelta(days=2))

    if await redis.get(f"progress:{nonce}:cancelled"):
        raise asyncio.CancelledError


class VerifyAllEndpoint(RelayEndpoint[Payload]):
    """An endpoint for chunking the guild and updating all members."""

    def __init__(self):
        super().__init__("VERIFYALL", Payload)

    async def handle_chunks(self, guild: discord.Guild, members: list[discord.Member], chunk_limit: int, nonce: str):
        """Handle the chunking of the members."""

        split_chunk = [members[i : i + chunk_limit] for i in range(0, len(members), chunk_limit)]

        await record_progress(nonce, 0, len(members), 0, len(split_chunk))

        try:
            for i, member_chunk in enumerate(split_chunk, 1):
                logging.debug(f"Sending chunk {i + 1} of {len(split_chunk)} chunks.")

                text, response = await fetch(
                    "POST",
                    f"{CONFIG.HTTP_BOT_API}/api/users/update",
                    headers={"Authorization": CONFIG.HTTP_BOT_AUTH},
                    body={
                        "guild_id": guild.id,
                        "members": [MemberSerializable.from_discordpy(m).model_dump() for m in member_chunk],
                        "nonce": nonce
                    },
                    parse_as="JSON",
                    timeout=None,
                    raise_on_failure=False
                )
                logging.debug(f"BOT SERVER RESPONSE: {response.status}, {text}")

                if response.status != StatusCodes.OK:
                    logging.error(f"Verify endpoint response: {response.status}, {text}")
                    break

                # Wait 3 seconds before sending the next request.
                logging.debug("Verify endpoint: sleeping for 3 seconds.")
                await asyncio.sleep(3)

                await record_progress(nonce, len(member_chunk), len(members), i, len(split_chunk))

        except asyncio.CancelledError:
            return

    async def handle(self, request: RedisRelayRequest[Payload]) -> Response:
        payload = request.payload
        chunk_limit = payload.chunk_limit
        nonce = request.nonce
        guild = bloxlink.get_guild(payload.guild_id)

        if not guild:
            return

        members = await guild.chunk()

        create_task_log_exception(self.handle_chunks(guild, members, chunk_limit, nonce))

        return Response(success=True, nonce=request.nonce)
