import logging
from datetime import datetime
from typing import Optional

from discord import AllowedMentions, AutoShardedClient, Game, Intents, Member

from resources.secrets import DISCORD_TOKEN, HTTP_BOT_API, HTTP_BOT_AUTH
from resources.utils import MinimalConversions, ReturnType, fetch

logger = logging.getLogger()
intents = Intents.none()
intents.members = True
intents.guilds = True

started_at: Optional[datetime] = None

client = AutoShardedClient(
    intents=intents,
    allowed_mentions=AllowedMentions(everyone=False, users=True, roles=False),
    activity=Game("Linking Accounts!"),
)


@client.event
async def on_ready():
    logger.info(f"Bot has been logged in & is ready as {client.user}")


@client.event
async def on_member_join(member: Member):
    text, response = await fetch(
        "POST",
        f"{HTTP_BOT_API}/api/update/join/{member.guild.id}/{member.id}",
        headers={"Authorization": HTTP_BOT_AUTH},
        body=MinimalConversions.convert_member(member),
        return_data=ReturnType.TEXT,
        timeout=None,
    )
    logger.debug(f"BOT SERVER RESPONSE: {response.status}, {text}")

    if response.status > 400:
        logger.error(f"BOT SERVER RESPONSE: {response.status}, {text}")


async def run():
    global started_at
    started_at = datetime.now()
    logger.info("Logging into Discord.")
    await client.login(DISCORD_TOKEN)
    logger.info("Connecting to Gateway.")
    await client.connect(reconnect=True)
