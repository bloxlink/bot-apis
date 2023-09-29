from sanic.response import json

from resources.constants import DEFAULTS
from resources.database import fetch_guild_data
from resources.models import GuildData
from resources.utils import find


class Route:
    PATH = "/binds/<user_id>/"
    METHODS = ("POST",)

    def flatten_binds(self, role_binds: list) -> list:
        all_binds: list = []

        for bind in role_binds:
            if bind.get("bind", {}).get("criteria"):
                map(all_binds.append, bind["bind"]["criteria"])
            else:
                all_binds.append(bind["bind"])

        return all_binds

    def has_custom_verified_roles(self, role_binds: list) -> tuple[bool, bool]:
        has_verified_role: bool = False
        has_unverified_role: bool = False

        all_binds: list = self.flatten_binds(role_binds)

        for bind in all_binds:
            if bind.get("type") == "verified":
                has_verified_role = True
            elif bind.get("type") == "unverified":
                has_unverified_role = True

        return has_verified_role, has_unverified_role

    async def get_default_verified_role(self, guild: dict) -> tuple[str, str]:
        guild_data: GuildData = await fetch_guild_data(
            guild["id"],
            "verifiedRoleEnabled",
            "verifiedRole",
            "verifiedRoleName",
            "unverifiedRoleEnabled",
            "unverifiedRole",
            "unverifiedRoleName",
        )

        verified_role: str | None = None
        unverified_role: str | None = None

        verified_role_name: str | None = (
            None if guild_data.verifiedRole else guild_data.verifiedRoleName or "Verified"
        )
        unverified_role_name: str | None = (
            None if guild_data.unverifiedRole else guild_data.unverifiedRoleName or "Unverified"
        )

        if guild_data.verifiedRoleEnabled or guild_data.unverifiedRoleEnabled:
            for role in filter(lambda r: not r["managed"], guild["roles"]):
                if role["name"] == verified_role_name or str(role["id"]) == guild_data.verifiedRole:
                    verified_role = role
                elif role["name"] == unverified_role_name or str(role["id"]) == guild_data.unverifiedRole:
                    unverified_role = role

        return verified_role, unverified_role

    async def check_bind_for(
        self, guild_roles: list[dict], roblox_account: dict, bind_type: str, bind_id: int, **bind_data
    ):
        bind_roles: set = set()
        remove_roles: set = set()

        bind_explanations: dict[str, list] = {"success": [], "failure": []}

        success: bool = False
        entire_group_bind: bool = "roles" not in bind_data  # find a role matching their roleset

        if bind_type == "group":
            if roblox_account:
                user_group: dict | None = roblox_account.get("groupsv2", {}).get(str(bind_id))

                if user_group:
                    if bind_data.get("roleset"):
                        bind_roleset = bind_data["roleset"]

                        if bind_roleset < 0 and abs(bind_roleset) <= user_group["role"]["rank"]:
                            success = True
                            bind_explanations["success"].append(
                                f"Your rank is equal to or greater than {bind_roleset}."
                            )
                        else:
                            bind_explanations["failure"].append(
                                f"This bind requires your rank, {user_group['role']['rank']}, to be higher than {bind_roleset}."
                            )

                        if bind_roleset == user_group["role"]["rank"]:
                            success = True
                            bind_explanations["success"].append(f"Your rank is equal to {bind_roleset}.")
                        else:
                            bind_explanations["failure"].append(
                                f"This bind requires your rank, {user_group['role']['rank']}, to be equal to {bind_roleset}."
                            )

                    elif bind_data.get("min") and bind_data.get("max"):
                        if int(bind_data["min"]) <= user_group["role"]["rank"] <= int(bind_data["max"]):
                            success = True
                            bind_explanations["success"].append(
                                f"Your rank is between {bind_data['min']} and {bind_data['max']}."
                            )
                        else:
                            bind_explanations["failure"].append(
                                f"This bind requires your rank to be between {bind_data['min']} and {bind_data['max']}; however, your rank is {user_group['role']['rank']}."
                            )

                    # elif bind_data.get("everyone"):
                    #     success = True
                    else:
                        success = True
                        bind_explanations["success"].append(f"You are in this group.")

                else:
                    # check if guest bind (not in group)
                    if bind_data.get("guest"):
                        success = True
                        bind_explanations["success"].append("You are not in this group.")
                    else:
                        bind_explanations["failure"].append(
                            f"This bind requires you to be in the group {bind_id}."
                        )

        elif bind_type in ("verified", "unverified"):
            if bind_type == "verified" and roblox_account:
                success = True
            elif bind_type == "unverified" and not roblox_account:
                success = True

            for bind_role_id in bind_data.get("roles", []):
                role = find(lambda r: str(r.id) == bind_role_id, guild_roles)
                if bind_role_id in find(lambda r: str(r.id) == bind_role_id, guild_roles):
                    if bind_type == "verified" and roblox_account:
                        bind_roles.add(bind_role_id)
                    elif bind_type == "unverified" and not roblox_account:
                        bind_roles.add(bind_role_id)

        if success:
            if entire_group_bind and not (roblox_account and user_group):
                raise RuntimeError(
                    "Bad bind: this bind must have roles if the user does not have a Roblox account."
                )

            # add in the remove roles
            if bind_data.get("removeRoles"):
                remove_roles.update(bind_data["removeRoles"])

            if entire_group_bind:
                # find role that matches their roleset
                for role in guild_roles:
                    if not role["managed"] and user_group["role"]["name"] == role.name:
                        bind_roles.add(role["id"])

                        break
                else:
                    # role was not found in server, so we need to create it
                    # TODO: check for dynamic roles?
                    # TODO: check for permissions
                    # role = await guild.create_role(name=user_group.my_role["name"]) # FIXME
                    # bind_roles.add(str(role.id))
                    pass

            else:
                # just add in the bind roles
                bind_roles.update(bind_data["roles"])

            if bind_data.get("roles"):
                bind_roles.update(bind_data["roles"])

        return success, bind_roles, remove_roles, bind_explanations

    async def handler(self, request, user_id):
        json_data: dict = request.json or {}

        guild: dict = json_data.get("guild")
        roblox_account = json_data.get("roblox_account")
        member: dict = json_data.get("member")

        guild_data: GuildData = await fetch_guild_data(guild["id"], "binds", "nicknameTemplate")

        role_binds: list = guild_data.binds or []

        user_binds = {
            "optional": [],
            "required": [],
            "explanations": {"success": [], "failure": [], "criteria": []},
        }

        is_restricted = json_data.get("restricted", False)

        default_nickname_template = guild_data.nicknameTemplate or DEFAULTS.get("nicknameTemplate")

        if not is_restricted:
            for bind_data in role_binds:
                # bind_nickname     = bind_data.get("nickname") or None
                role_bind: dict = bind_data.get("bind") or {}
                bind_required: bool = not bind_data.get("optional", False)

                bind_type: str = role_bind.get("type")
                bind_id: str | None = role_bind.get("id") or None
                bind_criteria: list = role_bind.get("criteria") or []

                bind_success: bool = None
                bind_roles: list = []
                bind_remove_roles: list = []

                criteria_add_roles: set = set()  # keep track of roles from the criteria
                criteria_remove_roles: set = set()  # keep track of roles from the criteria

                if bind_criteria:
                    criteria_explanations: dict[str, list | str] = {
                        "criteriaType": bind_type,
                        "success": [],
                        "failure": [],
                    }

                    for criterion in bind_criteria:
                        try:
                            (
                                criterion_success,
                                criterion_roles,
                                criterion_remove_roles,
                                criterion_explanations,
                            ) = await self.check_bind_for(
                                guild,
                                roblox_account,
                                criterion["type"],
                                criterion["id"],
                                **bind_data,
                                **criterion,
                            )
                        except RuntimeError as e:
                            return json({"success": False, "error": e}, status=400)

                        if bind_type == "requireAll":
                            if bind_success is None and criterion_success is True:
                                bind_success = True
                            elif (bind_success is True and criterion_success is False) or (
                                bind_success is None and criterion_success is False
                            ):
                                bind_success = False

                            if criterion_success:
                                criteria_add_roles.update(criterion_roles)
                                criteria_remove_roles.update(criterion_remove_roles)
                                criteria_explanations["success"] += criterion_explanations["success"]
                            else:
                                criteria_explanations["failure"] += criterion_explanations["failure"]
                                # break

                    user_binds["explanations"]["criteria"].append(criteria_explanations)

                else:
                    try:
                        (
                            bind_success,
                            bind_roles,
                            bind_remove_roles,
                            bind_explanations,
                        ) = await self.check_bind_for(
                            guild["roles"], roblox_account, bind_type, bind_id, **role_bind, **bind_data
                        )
                    except RuntimeError:
                        return json({"success": False, "error": e}, status=400)

                    if bind_explanations:
                        user_binds["explanations"]["success"] += bind_explanations["success"]
                        user_binds["explanations"]["failure"] += bind_explanations["failure"]

                if bind_success:
                    append_roles = list(
                        criteria_add_roles or bind_roles
                    )  # whether we append all roles from the criteria or just from the one bind
                    remove_roles = list(
                        criteria_remove_roles or bind_remove_roles
                    )  # whether we append all roles from the criteria or just from the one bind

                    user_binds["required" if bind_required else "optional"].append(
                        [bind_data, append_roles, remove_roles, bind_data.get("nickname")]
                    )

        # for when they didn't save their own [un]verified roles
        has_verified_role, has_unverified_role = self.has_custom_verified_roles(role_binds)

        if not (has_verified_role and has_unverified_role):
            # no? then we can check for the default [un]verified roles
            verified_role, unverified_role = await self.get_default_verified_role(guild)

            if not has_verified_role and verified_role and roblox_account and not is_restricted:
                user_binds["required"].append(
                    [
                        {"type": "verified"},
                        [str(verified_role["id"])],
                        [str(unverified_role["id"])]
                        if unverified_role and unverified_role["id"] in member["roles"]
                        else [],
                        default_nickname_template,
                    ]
                )

            if not has_unverified_role and unverified_role and (not roblox_account or is_restricted):
                user_binds["required"].append(
                    [
                        {"type": "unverified"},
                        [str(unverified_role["id"])],
                        [str(verified_role["id"])]
                        if verified_role and verified_role["id"] in member["roles"]
                        else [],
                        None,
                    ]
                )

        return json({"success": True, "binds": user_binds})
