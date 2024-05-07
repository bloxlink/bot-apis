import asyncio
from bloxlink_lib import get_accounts, reverse_lookup
from bloxlink_lib.database import fetch_guild_data
from discord import User, Member, Guild, NotFound
from app.bloxlink import bloxlink
from app.decorators import guild_premium_required


@bloxlink.event
@guild_premium_required
async def on_member_ban(guild: Guild, user: User | Member):
    """Event for when a user is banned from the guild."""

    guild_data = await fetch_guild_data(guild.id, "banRelatedAccounts")

    if guild_data.banRelatedAccounts:
        roblox_accounts = await get_accounts(user)

        for account in roblox_accounts:
            discord_ids = await reverse_lookup(account, user.id)

            for discord_id in discord_ids:
                try:
                    if member_alt := guild.get_member(discord_id) or await guild.fetch_member(discord_id):
                        await guild.ban(member_alt, reason=f"banRelatedAccounts is enabled - alt of {user} ({user.id})")
                except NotFound:
                    pass

                await asyncio.sleep(1)
