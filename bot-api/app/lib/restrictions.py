from typing import Any, Annotated
from pydantic import Field
from bloxlink_lib import RobloxUser, BaseModel
from bloxlink_lib.database import fetch_guild_data


class RestrictedData(BaseModel):
    """Data of the restriction."""

    unevaluated: Annotated[list, Field(default_factory=list)]
    is_restricted: bool = False
    reason: str | None = None
    action: str | None = "kick"
    source: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.reason or self.source:
            self.is_restricted = True

        if self.is_restricted and not self.action:
            self.action = "kick"



async def calculate_restrictions(guild_id: int, roblox_user: RobloxUser) -> RestrictedData:
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


    restricted = RestrictedData()

    guild_data = await fetch_guild_data(
        guild_id,
        "ageLimit",#
        "disallowAlts",
        "disallowBanEvaders",#
        "groupLock",
    )

    if roblox_user:
        if guild_data.disallowBanEvaders:
            restricted.unevaluated.append("disallowBanEvaders")

        if guild_data.disallowAlts:
            restricted.unevaluated.append("disallowAlts")

    if guild_data.ageLimit:
        if not roblox_user:
            restricted.reason = "User is not verified with Bloxlink."
            restricted.source = "ageLimit"

            return restricted

        if roblox_user.age_days < guild_data.ageLimit:
            # fmt:skip
            restricted.reason = f"User's account ({roblox_user.username}) age is less than" \
                f"{guild_data.ageLimit} days old."
            restricted.source = "ageLimit"

            return restricted

    if guild_data.groupLock:
        if not roblox_user:
            kick_unverified = any(
                g.get("unverifiedAction", "kick") == "kick" for g in guild_data.groupLock.values()
            )

            restricted.reason = "User is not verified with Bloxlink."
            restricted.action = "kick" if kick_unverified else None
            restricted.source = "groupLock"

            return restricted

        for group_id, group_data in guild_data.groupLock.items():
            group_lock_action = group_data.get("verifiedAction", "dm")
            required_rolesets = group_data.get("roleSets")
            dm_message = group_data.get("dmMessage") or ""

            if dm_message:
                dm_message = f"\n\n**The following text is from the server admins:**" \
                    f"\n>{dm_message} "

            group_match = roblox_user.get("groupsv2", {}).get(group_id)

            if not group_match:
                restricted.reason = f"User ({roblox_user.username}) is not in the group " \
                    f"{group_id}{dm_message}"
                restricted.action = group_lock_action
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
                # fmt:skip
                restricted.reason = f"User ({roblox_user.username}) does not have the required rank in the group " \
                    f"{group_id}.{dm_message}"
                restricted.action = group_lock_action
                restricted.source = "groupLock"

                return restricted

    return restricted
