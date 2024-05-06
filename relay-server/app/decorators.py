from typing import Callable, get_type_hints
from functools import wraps
from bloxlink_lib import fetch_typed, StatusCodes
import discord
from app.types import PremiumResponse
from app.config import CONFIG


def guild_premium_required(fn: Callable):
    """
    executes the callback if the guild has premium
    expects the callback to have either a guild or member parameter
    """

    @wraps(fn)
    async def wrapper(*args):
        type_hints = get_type_hints(fn)
        guild: discord.Guild | None = None

        # find the guild from the type hints
        for i, arg_hint in enumerate(type_hints.values()):
            if arg_hint == discord.Guild:
                guild = args[i]
            elif arg_hint == discord.Member:
                guild = args[i].guild

        if not guild:
            raise ValueError("Function must have either a member or guild parameter")

        json_response, response = await fetch_typed(
            PremiumResponse,
            f"{CONFIG.HTTP_BOT_API}/api/premium/guilds/{guild.id}",
            headers={"Authorization": CONFIG.HTTP_BOT_AUTH},
        )

        if response.status == StatusCodes.OK and json_response.premium:
            return await fn(*args)

    return wrapper
