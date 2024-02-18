import time
import json
from datetime import timedelta, datetime
from bloxlink_lib import parse_into, BaseModel, create_task_log_exception
from bloxlink_lib.database import redis
import discord
from ..base import RelayEndpoint
from ..redis import RedisRelayRequest
from ..bloxlink import bloxlink


class Response(BaseModel):
    """Response from the stats command."""

    success: bool
    nonce: str

class Payload(BaseModel):
    guild_id: int
    channel_id: int
    chunk_limit: int

class VerifyAllProgress(BaseModel):
    started: datetime
    progress: int
    total: int


async def record_progress(nonce: str, progress: int, total: int):
    """Record the progress of the verification."""

    current_progress: dict = json.loads(await redis.get(f"progress:{nonce}")) if await redis.exists(f"progress:{nonce}") else {}

    if not current_progress:
        current_progress = {
            "started": datetime.now(),
            "progress": progress,
            "total": total
        }

    parsed_progress = parse_into(current_progress, VerifyAllProgress)

    parsed_progress.progress = progress
    parsed_progress.total = total

    await redis.set(f"progress:{nonce}", parsed_progress.model_dump_json(), ex=int(timedelta(days=2).total_seconds()))



class VerifyAllEndpoint(RelayEndpoint[Payload]):
    """An endpoint for chunking the guild and updating all members."""

    def __init__(self):
        super().__init__("VERIFYALL", Payload)

    async def handle_chunks(self, guild: discord.Guild, members: list[discord.Member], chunk_limit: int, nonce: str):
        """Handle the chunking of the members."""

        await record_progress(nonce, 0, len(members))

        split_chunk = [members[i : i + chunk_limit] for i in range(0, len(members), chunk_limit)]

        for member_chunk in split_chunk:
            pass

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
