from sanic.response import json

from resources.binds import get_binds
from resources.database import fetch_guild_data
from resources.models import GuildData


class Route:
    """Calculate data for updating a user."""

    PATH = "/restrictions/evaluate/<guild_id>/"
    METHODS = ("POST",)
    NAME = "evaluate_restrictions_for_user"

    def calculate_restrictions(self, guild_data: GuildData, roblox_user: dict) -> dict:
        """Check the restrictions in the guild against this roblox_user.

        This does not check for banEvaders or alt accounts. It will, however, include
        that in the output in the "unevaluated" field.

        #### Args:
            guild_data (GuildData): Settings for the guild.
            roblox_user (dict): The roblox user data we are checking restrictions against.

        #### Returns:
            dict: The result from the restriction checks.

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
        output = {
            "unevaluated": [],
            "is_restricted": False,
        }

        if guild_data.disallowBanEvaders and roblox_user:
            output["unevaluated"].append("disallowBanEvaders")

        if guild_data.disallowAlts and roblox_user:
            output["unevaluated"].append("disallowAlts")

        if guild_data.ageLimit:
            if not roblox_user:
                output["is_restricted"] = True
                output["reason"] = "User is not verified with Bloxlink."
                output["action"] = "kick"
                output["source"] = "ageLimit"

                return output

            age = roblox_user.get("age_days", 0)
            if age < guild_data.ageLimit:
                roblox_name = roblox_user["name"]

                output["is_restricted"] = True
                output["reason"] = f"User's account ({roblox_name}) age is less than {guild_data.ageLimit} days old."  # fmt:skip
                output["action"] = "kick"
                output["source"] = "ageLimit"

                return output

        if guild_data.groupLock:
            if not roblox_user:
                kick_unverified = any(
                    g.get("unverifiedAction", "kick") == "kick" for g in guild_data.groupLock.values()
                )

                output["is_restricted"] = True
                output["reason"] = "User is not verified with Bloxlink."
                output["action"] = "kick" if kick_unverified else "dm"
                output["source"] = "groupLock"

                return output

            for group_id, group_data in guild_data.groupLock.items():
                roblox_name = roblox_user["name"]

                action = group_data.get("verifiedAction", "dm")
                required_rolesets = group_data.get("roleSets")

                dm_message = group_data.get("dmMessage") or ""
                if dm_message:
                    dm_message = f"\n\n**The following text is from the server admins:**\n> {dm_message}"

                group_match = roblox_user.get("groupsv2", {}).get(group_id)
                if group_match is None:
                    output["is_restricted"] = True
                    output["reason"] = f"User ({roblox_name}) is not in the group {group_id}.{dm_message}"
                    output["action"] = action
                    output["source"] = "groupLock"

                    return output

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
                    output["is_restricted"] = True
                    output["reason"] = f"User ({roblox_name}) is not the required rank in the group {group_id}.{dm_message}"  # fmt:skip
                    output["action"] = action
                    output["source"] = "groupLock"

                    return output

        return output

    async def handler(self, request, guild_id):
        """Entry point for the /evaluate/guild_id endpoint

        Request body should contain Roblox user data as the roblox_account key.
        """
        guild_id = str(guild_id)

        json_data: dict = request.json or {}

        roblox_account = json_data.get("roblox_account")

        guild_data: GuildData = await fetch_guild_data(
            guild_id,
            "ageLimit",
            "disallowAlts",
            "disallowBanEvaders",
            "groupLock",
        )
        # Call get_binds so we can get the converted bind format (if those weren't converted prior.)
        guild_data.binds = await get_binds(guild_id)

        restrict_data = self.calculate_restrictions(guild_data=guild_data, roblox_user=roblox_account)

        return json({"success": True, **restrict_data})
