from sanic.response import json

from resources.binds import GroupBind, GuildBind, get_binds
from resources.database import fetch_guild_data, update_guild_data
from resources.models import GuildData
from resources.roblox_group import RobloxGroup
from resources.roblox_user import get_asset_ownership
from routes.binds.roles import calculate_final_roles
from routes.nickname.parse import parse_nickname


class Route:
    """Calculate data for updating a user."""

    PATH = "/update/<guild_id>/<user_id>/"
    METHODS = ("POST",)
    NAME = "guild_update_user"

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

    async def calculate_verification_roles(self, guild_data: GuildData, discord_guild: dict) -> dict:
        """Determine what verification roles to use, between the default or custom binds.

        Verification roles consist of both the unverified + verified roles.

        #### Args:
            guild_data (GuildData): Settings for the guild.
            discord_guild (dict): Discord data of the guild.

        #### Returns:
            dict: The found verified & unverified roles (if they exist).

            Example: {
                "verified": {},
                "unverified": {},
                "custom_verified": False,
                "custom_unverified": False,
                "missing_verified": False,
                "missing_unverified": False,
            }

            Verified & unverified keys can either be a dict (default role) or a list (custom roles).\n
            Use custom_(un)verified entries to determine if it should be handled as a dict or list.\n
            The missing_* keys are used to determine if the role needs to be created (for default verified/
            unverified roles only)
        """
        output = {
            "verified": None,
            "unverified": None,
            "custom_verified": False,
            "custom_unverified": False,
            "missing_verified": False,
            "missing_unverified": False,
        }

        default_verified, default_unverified = await self.get_default_verification_roles(
            discord_guild, guild_data
        )
        custom_verified, custom_unverified = self.get_custom_verification_roles(guild_data.binds)

        if not custom_verified:
            output["verified"] = default_verified
            if not default_verified.get("id"):
                output["missing_verified"] = True
        else:
            output["verified"] = custom_verified
            output["custom_verified"] = True

        if not custom_unverified:
            output["unverified"] = default_unverified
            if not default_unverified.get("id"):
                output["missing_unverified"] = True
        else:
            output["unverified"] = custom_unverified
            output["custom_unverified"] = True

        return output

    async def calculate_binds(self, guild_data: GuildData, roblox_user: dict) -> dict:
        """Determine what binds apply to this roblox_user.

        This does not include custom verification role binds (at the top level). Those are handled
        in calculate_verification_roles.

        #### Args:
            guild_data (GuildData): Settings for the guild.
            roblox_user (dict): Roblox data of the user verifying.

        #### Returns:
            dict: Which binds could be successfully given, which binds cannot, and linked groups to check.

            Structure: {
                "successful": [],
                "failed": [],
                "linked_group": []
            }

            Bindings will be represented as their GuildBind/GroupBind.

            Linked groups are put in their own section so other functions can evaluate it later & determine
            which roles correspond to the group ranks. Only successful linked groups are added to the
            linked_group list.
        """
        # Remove TOP LEVEL verified/unverified bindings bc we get that in the verification section.
        binds = [bind for bind in guild_data.binds if bind.type not in ("verified", "unverified")]
        output = {"successful": [], "failed": [], "linked_group": []}

        for bind in binds:
            bind: GuildBind

            if bind.type in ("group", "asset", "badge", "gamepass") and not roblox_user:
                output["failed"].append(bind)
                continue

            match bind.type:
                case "group":
                    bind: GroupBind
                    user_group: dict | None = roblox_user.get("groupsv2", {}).get(str(bind.id))

                    if not user_group:
                        if bind.guest or bind.roleset == 0:
                            output["successful"].append(bind)
                        else:
                            output["failed"].append(bind)

                        continue

                    if bind.subtype == "linked_group":
                        output["linked_group"].append(bind)
                        continue

                    # All non-entire group bindings.
                    user_rank = user_group["role"]["rank"]

                    if bind.roleset:
                        if (bind.roleset < 0 and abs(bind.roleset) <= user_rank) or bind.roleset == user_rank:  # fmt: skip
                            output["successful"].append(bind)
                        else:
                            output["failed"].append(bind)

                    elif bind.min and bind.max:
                        if bind.min <= user_rank <= bind.max:
                            output["successful"].append(bind)
                        else:
                            output["failed"].append(bind)

                    elif bind.min:
                        if bind.min <= user_rank:
                            output["successful"].append(bind)
                        else:
                            output["failed"].append(bind)

                    elif bind.max:
                        if user_rank <= bind.max:
                            output["successful"].append(bind)
                        else:
                            output["failed"].append(bind)

                    elif bind.guest:
                        output["failed"].append(bind)

                    elif bind.everyone:
                        output["successful"].append(bind)

                case "asset" | "badge" | "gamepass":
                    success = await get_asset_ownership(roblox_user["id"], bind.type, bind.id)

                    if success:
                        output["successful"].append(bind)
                    else:
                        output["failed"].append(bind)

                case _:
                    pass

        return output

    async def calculate_nickname(
        self,
        discord_guild: dict,
        roblox_user: dict,
        member_data: dict,
        bindings: list[GuildBind],
        final_roles: list[str] = None,
    ) -> str:
        """Determine which nickname should be given to this user.

        #### Args:
            discord_guild (dict): Discord data of this guild.
            roblox_user (dict): Roblox user data of the user verifying.
            member_data (dict): Guild member data of the user verifying.
            bindings (list[GuildBind]): The bindings of this guild (that apply to the user -
                aka successful bindings).
            final_roles (list[str], optional): All the roles the user will end up with. Defaults to None.
                Used for determining the linked group nickname template to apply.

        #### Returns:
            str: The resulting nickname to give to the user.
        """
        guild_id = discord_guild["id"]
        guild_name = discord_guild.get("name")
        guild_roles = discord_guild.get("roles")
        final_roles = final_roles or []

        nickname_to_role = []
        for bind in bindings:
            if isinstance(bind, GroupBind):
                if bind.subtype == "linked_group":
                    group = RobloxGroup(bind.id)
                    rank_mappings = await group.rolesets_to_roles(discord_guild.get("roles", []))

                    for role in final_roles:
                        if role in rank_mappings.values():
                            role = next((x for x in guild_roles if role == str(x["id"])), None)
                            nickname_to_role.append((bind, role))
                    continue

            if bind.nickname and bind.roles:
                for role in bind.roles:
                    role = next((x for x in guild_roles if role == str(x["id"])), None)
                    nickname_to_role.append((bind, role))

        final_match = sorted(
            nickname_to_role,
            key=lambda x: (x[1].get("position"), x[1]["id"]) if x else (),
            reverse=True,
        )
        if final_match:
            final_match = final_match[0]
            nickname_template = final_match[0].nickname

            return await parse_nickname(
                user_data={
                    "name": member_data.get("name"),
                    "nick": member_data.get("nick"),
                    "id": member_data.get("id"),
                },
                template=nickname_template,
                is_nickname=True,
                guild_id=guild_id,
                guild_name=guild_name,
                group_id=final_match[0].id if final_match[0].type == "group" else None,
                roblox_user=roblox_user,
            )

        return await parse_nickname(
            user_data={
                "name": member_data.get("name"),
                "nick": member_data.get("nick"),
                "id": member_data.get("id"),
            },
            template="",
            is_nickname=True,
            guild_id=guild_id,
            guild_name=guild_name,
            roblox_user=roblox_user,
        )

    def get_custom_verification_roles(self, role_binds: list[GuildBind]) -> tuple[list, list]:
        """Get (non-criteria) bindings that are related to verification.

        I.e. a verified or unverified role that is set via a binding, rather than via the top level
        unverifiedRole and verifiedRole database keys.

        This does not consider binds nested in criteria as a custom role.

        #### Args:
            role_binds (list[GuildBind]): The bindings in the guild
        """
        verified_binds = []
        unverified_binds = []

        for bind in role_binds:
            if bind.type == "verified":
                verified_binds.append(bind)
            elif bind.type == "unverified":
                unverified_binds.append(bind)

        return verified_binds, unverified_binds

    async def get_default_verification_roles(self, guild: dict, guild_data: GuildData) -> tuple[dict, dict]:
        """Get the non-custom unverified & verified roles in the given guild.

        #### Args:
            guild (dict): Guild data as a dict, needs an "id" and the "roles" list keys at a minimum.

        #### Returns:
            tuple[dict, dict]: The found (verified, unverified) roles.
                Will be None if not found.
                Keys for the found roles will be "id", "name", and "managed".
        """
        verified_role: dict | None = None
        unverified_role: dict | None = None

        # fmt:off
        verified_role_name: str | None = None if guild_data.verifiedRole else guild_data.verifiedRoleName or "Verified"
        unverified_role_name: str | None = None if guild_data.unverifiedRole else guild_data.unverifiedRoleName or "Unverified"
        # fmt:on

        verified_role_id = str(guild_data.verifiedRole)
        unverified_role_id = str(guild_data.unverifiedRole)

        for role in filter(lambda r: not r["managed"], guild["roles"]):
            role_name = role["name"]
            role_id = str(role["id"])

            if not verified_role and (role_name == verified_role_name or role_id == verified_role_id):
                verified_role = role

            if not unverified_role and (role_name == unverified_role_name or role_id == unverified_role_id):
                unverified_role = role

        # Save the (un)verified role's ID & unset the role name option (only when a name is set).
        if verified_role and verified_role_name:
            await update_guild_data(
                str(guild_data.id), verifiedRole=str(verified_role["id"]), verifiedRoleName=None
            )

        if unverified_role and unverified_role_name:
            await update_guild_data(
                str(guild_data.id), unverifiedRole=str(unverified_role["id"]), unverifiedRoleName=None
            )

        # No (un)verified role was found. Tell the code to make one + save name in db.
        # Unset the existing ID if there is one, the role wasn't found so that means it was deleted
        if guild_data.verifiedRoleEnabled and not verified_role:
            verified_role = {"name": verified_role_name or "Verified"}

            if verified_role_id:
                await update_guild_data(
                    str(guild_data.id),
                    verifiedRole=None,
                )

        if guild_data.unverifiedRoleEnabled and not unverified_role:
            unverified_role = {"name": unverified_role_name or "Unverified"}

            if unverified_role_id:
                await update_guild_data(
                    str(guild_data.id),
                    unverifiedRole=None,
                )

        return verified_role, unverified_role

    # pylint: disable-next=unused-argument
    async def handler(self, request, guild_id, user_id):
        """Entry point for the /update/guild_id/user_id endpoint"""
        guild_id = str(guild_id)

        json_data: dict = request.json or {}

        guild: dict = json_data.get("guild")
        roblox_account = json_data.get("roblox_account")
        member: dict = json_data.get("member")

        guild_data: GuildData = await fetch_guild_data(
            guild_id,
            "verifiedRoleEnabled",
            "verifiedRole",
            "verifiedRoleName",
            "unverifiedRoleEnabled",
            "unverifiedRole",
            "unverifiedRoleName",
            "ageLimit",
            "disallowAlts",
            "disallowBanEvaders",
            "groupLock",
        )
        # Call get_binds so we can get the converted bind format (if those weren't converted prior.)
        guild_data.binds = await get_binds(guild_id)

        final_response = {
            "nickname": None,
            "roles": {
                "final": [],
                "added": [],
                "removed": [],
                "missing": [],
            },
            "restrictions": {},
        }

        restrict_data = self.calculate_restrictions(guild_data=guild_data, roblox_user=roblox_account)
        final_response["restrictions"] = restrict_data
        is_restricted = restrict_data["is_restricted"]

        verified_data = await self.calculate_verification_roles(guild_data=guild_data, discord_guild=guild)

        bind_data = await self.calculate_binds(guild_data=guild_data, roblox_user=roblox_account)

        # Figure out which roles the user will ultimately keep.
        user_role_ids = [str(role) for role in member["roles"].keys()]
        give_roles = []
        take_roles = []

        # All the binds that qualify for a user - used for nickname handling.
        applicable_binds = []

        # Treat as unverified.
        if not roblox_account or is_restricted:
            if verified_data["custom_unverified"]:
                for bind in verified_data["unverified"]:
                    give_roles.extend(bind.roles)
                    take_roles.extend(bind.removeRoles)
            else:
                if guild_data.unverifiedRoleEnabled:
                    if verified_data["missing_unverified"]:
                        final_response["roles"]["missing"].append(verified_data["unverified"]["name"])
                    else:
                        give_roles.append(verified_data["unverified"]["id"])

            if not verified_data["missing_verified"] and not verified_data["custom_verified"]:
                take_roles.append(verified_data["verified"]["id"])

        if roblox_account and not is_restricted:
            if verified_data["custom_verified"]:
                for bind in verified_data["verified"]:
                    give_roles.extend(bind.roles)
                    take_roles.extend(bind.removeRoles)
            else:
                if guild_data.verifiedRoleEnabled:
                    if verified_data["missing_verified"]:
                        final_response["roles"]["missing"].append(verified_data["verified"]["name"])
                    else:
                        give_roles.append(verified_data["verified"]["id"])

            if not verified_data["missing_unverified"] and not verified_data["custom_unverified"]:
                take_roles.append(verified_data["unverified"]["id"])

        # Only try giving binds when not restricted
        if not is_restricted:
            applicable_binds.extend(bind_data["successful"])
            applicable_binds.extend(bind_data["linked_group"])

            for bind in bind_data["successful"]:
                give_roles.extend(bind.roles)
                take_roles.extend(bind.removeRoles)

            # Entire group bindings.
            for eg_bind in bind_data["linked_group"]:
                group = RobloxGroup(eg_bind.id)
                rank_mappings = await group.rolesets_to_roles(guild.get("roles", []))

                user_group: dict = roblox_account.get("groupsv2", {}).get(str(eg_bind.id))
                user_rank = user_group["role"]["name"]
                if not rank_mappings.get(user_rank):
                    if user_rank not in final_response["roles"]["missing"]:
                        final_response["roles"]["missing"].append(user_rank)
                else:
                    give_roles.append(rank_mappings.get(user_rank))

        give_roles = set(give_roles)
        take_roles = set(take_roles)

        user_role_data = await calculate_final_roles(
            data={
                "user_roles": user_role_ids,
                "successful_binds": {
                    "give": list(give_roles),
                    "remove": list(take_roles),
                },
            },
            guild_id=guild_id,
            guild_roles=guild["roles"],
        )

        final_response["roles"]["final"] = user_role_data["final_roles"]
        final_response["roles"]["added"] = user_role_data["added_roles"]
        final_response["roles"]["removed"] = user_role_data["removed_roles"]

        final_response["nickname"] = await self.calculate_nickname(
            discord_guild=guild,
            roblox_user=roblox_account if not is_restricted else {},
            member_data=member,
            bindings=applicable_binds,
            final_roles=final_response["roles"]["final"],
        )

        return json({"success": True, **final_response})
