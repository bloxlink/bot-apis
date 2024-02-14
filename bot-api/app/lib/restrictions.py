from typing import TypedDict
from bloxlink_lib import RobloxUser
from bloxlink_lib.database import fetch_guild_data


class RestrictedDict(TypedDict):
    """A dict to represent a restricted user."""

    unevaluated: list
    is_restricted: bool
    reason: str
    action: str
    source: str


async def calculate_restrictions(guild_id: int, roblox_user: RobloxUser) -> RestrictedDict:
    """Check the restrictions in the guild against this roblox_user.

    This does not check for banEvaders or alt accounts. It will, however, include
    that in the output in the "unevaluated" field.

    #### Args:
        guild_data (GuildData): Settings for the guild.
        roblox_user (RobloxUser): The roblox user data we are checking restrictions against.

    #### Returns:
        Restricted: The result from the restriction checks.

        Example: {
            "unevaluated": [],
            "is_restricted": True,
            "reason": "Reason for being restricted",
            "action": "Action to take against the user",
            "source": "Source for the restriction, aka the setting that matched"
        }

        The reason, action, and source keys are only included if is_restricted is True.
        Unevaluated at this time will only ever contain disallowBanEvaders and disallowAlts.
    """


    restricted = RestrictedDict(
        unevaluated=[],
        is_restricted=False,
        reason=None,
        action=None,
        source=None,
    )

    guild_data = await fetch_guild_data(
        guild_id,
        "ageLimit",
        "disallowAlts",
        "disallowBanEvaders",
        "groupLock",
    )

    if roblox_user:
        if guild_data.disallowBanEvaders:
            restricted.unevaluated.append("disallowBanEvaders")

        if guild_data.disallowAlts:
            restricted.unevaluated.append("disallowAlts")

    if guild_data.ageLimit:
        if not roblox_user:
            restricted.is_restricted = True
            restricted.reason = "User is not verified with Bloxlink."
            restricted.action = "kick"
            restricted.source = "ageLimit"

            return restricted

        age = roblox_user.get("age_days", 0)

        if age < guild_data.ageLimit:
            roblox_name = roblox_user["name"]

            restricted.is_restricted = True
            # fmt:skip
            restricted.reason = f"User's account ({roblox_name}) age is less than" \
                f"{guild_data.ageLimit} days old."
            restricted.action = "kick"
            restricted.source = "ageLimit"

            return restricted

    if guild_data.groupLock:
        if not roblox_user:
            kick_unverified = any(
                g.get("unverifiedAction", "kick") == "kick" for g in guild_data.groupLock.values()
            )

            restricted.is_restricted = True
            restricted.reason = "User is not verified with Bloxlink."
            restricted.action = "kick" if kick_unverified else "dm"
            restricted.source = "groupLock"

            return restricted

        for group_id, group_data in guild_data.groupLock.items():
            roblox_name = roblox_user["name"]

            action = group_data.get("verifiedAction", "dm")
            required_rolesets = group_data.get("roleSets")

            dm_message = group_data.get("dmMessage") or ""
            if dm_message:
                dm_message = f"\n\n**The following text is from the server admins:**" \
                    f"\n>{dm_message} "

            group_match = roblox_user.get("groupsv2", {}).get(group_id)
            if group_match is None:
                restricted.is_restricted = True
                restricted.reason = f"User ({roblox_name}) is not in the group " \
                    f"{group_id}.{dm_message}"
                restricted.action = action
                restricted.source = "groupLock"

                return restricted

            user_roleset = group_match["role"].get("rank")
            for roleset in required_rolesets:
                if isinstance(roleset, list):
                    # within range
                    if roleset[0] <= user_roleset <= roleset[1]:
                        break
                else:
                    # exact match (x) or inverse match (rolesets above x)
                    if (user_roleset == roleset) or (roleset < 0 and abs(roleset) <= user_roleset):
                        break
            else:
                # no match was found - restrict the user.
                restricted.is_restricted = True
                # fmt:skip
                restricted.reason = f"User ({roblox_name}) is not the required rank in the group " \
                    f"{group_id}.{dm_message}"
                restricted.action = action
                restricted.source = "groupLock"

                return restricted

    return restricted
