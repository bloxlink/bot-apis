import asyncio
from bloxlink_lib import get_accounts, reverse_lookup
from bloxlink_lib.database import fetch_guild_data
from discord import User, Member, Guild, NotFound, Object
from app.bloxlink import bloxlink
from app.decorators import guild_premium_required


@bloxlink.event
@guild_premium_required
async def on_member_unban(guild: Guild, user: User | Member):
    """Event for when a user is unbanned from the guild."""

    guild_data = await fetch_guild_data(guild.id, "unbanRelatedAccounts")

    if guild_data.unbanRelatedAccounts:
        roblox_accounts = await get_accounts(user)

        for account in roblox_accounts:
            discord_ids = await reverse_lookup(account, user.id)

            for discord_id in discord_ids:
                try:
                    if ban_entry := await guild.fetch_ban(Object(discord_id)):
                        await guild.unban(ban_entry.user, reason=f"unbanRelatedAccounts is enabled - alt of {user} ({user.id})")
                except NotFound:
                    pass

                await asyncio.sleep(1)
