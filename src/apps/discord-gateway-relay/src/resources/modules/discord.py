from discord import (
    AutoShardedClient,
    AllowedMentions,
    Intents,
    Game,
)
from typing import Optional
from datetime import datetime
import logging

from resources.secrets import DISCORD_TOKEN  # type: ignore[attr-defined]

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


async def run():
    global started_at
    started_at = datetime.now()
    logger.info("Logging into Discord.")
    await client.login(DISCORD_TOKEN)
    logger.info("Connecting to Gateway.")
    await client.connect(reconnect=True)
