import re
from bloxlink_lib import GuildBind, RobloxUser, MemberSerializable, RoleSerializable, get_binds, SnowflakeSet, CoerciveSet
from bloxlink_lib.database import fetch_guild_data


ARBITRARY_GROUP_TEMPLATE = re.compile(r"\{group-rank-(.*?)\}")
NICKNAME_TEMPLATE_REGEX = re.compile(r"\{(.*?)\}")


async def filter_binds(guild_id: int, roblox_user: RobloxUser | None, member: MemberSerializable, guild_roles: dict[int, RoleSerializable]) -> tuple[list[GuildBind], SnowflakeSet, CoerciveSet[str]]:
    """Filter the binds that apply to the user."""

    successful_binds: list[GuildBind] = []
    remove_roles = SnowflakeSet()
    missing_roles = CoerciveSet(str)

    guild_data = await fetch_guild_data(guild_id, "verifiedRoleEnabled", "unverifiedRoleEnabled")
    binds = await get_binds(guild_id, guild_roles=guild_roles)
    verified_role_enabled = guild_data.verifiedRoleEnabled
    unverified_role_enabled = guild_data.unverifiedRoleEnabled

    for bind in binds:
        if (bind.type == "verified" and not verified_role_enabled) or (bind.type == "unverified" and not unverified_role_enabled):
            continue

        bind_applies, bind_additional_roles, bind_missing_roles, bind_ineligible_roles = await bind.satisfies_for(guild_roles, member, roblox_user)

        if bind_applies:
            bind.roles.extend([str(x) for x in bind_additional_roles])
            successful_binds.append(bind)
            remove_roles.update(bind.remove_roles, bind_ineligible_roles)
            missing_roles.update(bind_missing_roles)
            bind.calculate_highest_role(guild_roles)
        else:
            remove_roles.update(bind_ineligible_roles)

            for role_id in bind.roles:
                if int(role_id) in member.role_ids:
                    remove_roles.add(role_id)

    # create any missing verified/unverified roles
    if roblox_user and verified_role_enabled and not any(b.type == "verified" for b in binds):
        missing_roles.add("Verified")
    elif not roblox_user and unverified_role_enabled and not any(b.type == "unverified" for b in binds):
        missing_roles.add("Unverified")

    return successful_binds, remove_roles, missing_roles
