import discord
from bloxlink_lib.database import update_guild_data
from app.bloxlink import bloxlink
from app.config import CONFIG


@bloxlink.event
async def on_guild_remove(guild: discord.Guild):
    """Event for when the bot leaves a guild."""

    if CONFIG.BOT_RELEASE == "PRO":
        await update_guild_data(guild.id, proBot=False)
