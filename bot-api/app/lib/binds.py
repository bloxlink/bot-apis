import re
from bloxlink_lib import GuildBind, RobloxUser, MemberSerializable, RoleSerializable, find
from bloxlink_lib.database import fetch_guild_data


ARBITRARY_GROUP_TEMPLATE = re.compile(r"\{group-rank-(.*?)\}")
NICKNAME_TEMPLATE_REGEX = re.compile(r"\{(.*?)\}")


async def filter_binds(guild_id: int, binds: list[GuildBind], roblox_user: RobloxUser | None, member: MemberSerializable, guild_roles: dict[str, RoleSerializable]) -> tuple[list[GuildBind], list[str], list[str]]:
    """Filter the binds that apply to the user."""

    successful_binds: list[GuildBind] = []
    remove_roles: list[str] = []
    missing_roles: list[str] = []

    guild_data = await fetch_guild_data(guild_id, "verifiedRoleEnabled", "unverifiedRoleEnabled")

    for bind in binds:
        if (bind.type == "verified" and not guild_data.verifiedRoleEnabled) or (bind.type == "unverified" and not guild_data.unverifiedRoleEnabled):
            continue

        bind_applies, bind_additional_roles, bind_missing_roles, bind_ineligible_roles = await bind.satisfies_for(guild_roles, member, roblox_user)

        if bind_applies:
            bind.roles.extend(bind_additional_roles)
            successful_binds.append(bind)
            remove_roles.extend(bind.remove_roles)
            missing_roles.extend(bind_missing_roles)
            bind.calculate_highest_role(guild_roles)
        else:
            remove_roles.extend(bind_ineligible_roles)

    return successful_binds, remove_roles, missing_roles


async def get_nickname_template(guild_id, potential_binds: list[GuildBind]) -> tuple[str, GuildBind | None]:
    """Get the unparsed nickname template for the user."""

    guild_data = await fetch_guild_data(
        guild_id,
        "nicknameTemplate",
    )

    # first sort the binds by role position
    potential_binds.sort(key=lambda b: b.highest_role.position, reverse=True)

    highest_priority_bind: GuildBind = potential_binds[0] if potential_binds else None

    nickname_template = highest_priority_bind.nickname if highest_priority_bind else guild_data.nicknameTemplate

    return nickname_template, highest_priority_bind


async def parse_template(guild_id: int, guild_name: str, potential_binds: list[GuildBind], member: MemberSerializable, roblox_user: RobloxUser | None = None, max_length=True) -> str | None:
    """
    Calculate the nickname for the user.

    The algorithm is as follows:
    - Find the highest priority bind that has a nickname. The priority is determined by the position of the role in the guild.
    - If no such bind is found, the template is guild_data.nicknameTemplate.

    The template is then adjusted to the user's data.
    """

    nickname_template, highest_priority_bind = await get_nickname_template(guild_id, potential_binds)
    smart_name: str = ""

    if nickname_template == "{disable-nicknaming}":
        return None

    # if the nickname template contains a group template, sync the group
    if "group-" in nickname_template:
        # get the group from the highest bind if it's a group bind; otherwise, find the first linked group bind
        group_bind = highest_priority_bind if highest_priority_bind and highest_priority_bind.type == "group" else find(lambda b: b.type == "group", potential_binds)

        if group_bind:
            await group_bind.entity.sync()
    else:
        group_bind = None

    # parse {smart-name}
    if roblox_user:
        if roblox_user.display_name != roblox_user.username:
            smart_name = f"{roblox_user.display_name} (@{roblox_user.username})"

            if len(smart_name) > 32:
                smart_name = roblox_user.username
        else:
            smart_name = roblox_user.username

        # parse {group-rank}
        if roblox_user:
            if "group-rank" in nickname_template:
                if group_bind and group_bind.criteria.id in roblox_user.groups:
                    group_roleset_name = roblox_user.groups[highest_priority_bind.criteria.id].role.name
                else:
                    group_roleset_name = "Guest"
            else:
                group_roleset_name = "Guest"

            # parse {group-rank-<group_id>} in the nickname template
            for group_id in ARBITRARY_GROUP_TEMPLATE.findall(nickname_template):
                group = roblox_user.groups.get(group_id)
                group_role_from_group = group.role.name if group else "Guest"

                nickname_template = nickname_template.replace("{group-rank-"+group_id+"}", group_role_from_group)

    # parse the nickname template
    for outer_nick in NICKNAME_TEMPLATE_REGEX.findall(nickname_template):
        nick_data = outer_nick.split(":")
        nick_fn: str | None = nick_data[0] if len(nick_data) > 1 else None
        nick_value: str = nick_data[1] if len(nick_data) > 1 else nick_data[0]

        # nick_fn = capA
        # nick_value = roblox-name

        if roblox_user:
            match nick_value:
                case "roblox-name":
                    nick_value = roblox_user.username
                case "display-name":
                    nick_value = roblox_user.display_name
                case "smart-name":
                    nick_value = smart_name
                case "roblox-id":
                    nick_value = str(roblox_user.id)
                case "roblox-age":
                    nick_value = str(roblox_user.age_days)
                case "group-rank":
                    nick_value = group_roleset_name

        match nick_value:
            case "discord-name":
                nick_value = member.username
            case "discord-nick":
                nick_value = member.nickname if member.nickname else member.username
            case "discord-mention":
                nick_value = member.mention
            case "discord-id":
                nick_value = str(member.id)
            case "server-name":
                nick_value = guild_name
            case "prefix":
                nick_value = "/"
            case "group-url":
                nick_value = group_bind.entity.url if group_bind else ""
            case "group-name":
                nick_value = group_bind.entity.name if group_bind else ""
            case "smart-name":
                nick_value = smart_name

        if nick_fn:
            if nick_fn in ("allC", "allL"):
                if nick_fn == "allC":
                    nick_value = nick_value.upper()
                elif nick_fn == "allL":
                    nick_value = nick_value.lower()

                nickname_template = nickname_template.replace("{{{0}}}".format(outer_nick), nick_value)
            else:
                nickname_template = nickname_template.replace("{{{0}}}".format(outer_nick), outer_nick) # remove {} only
        else:
            nickname_template = nickname_template.replace("{{{0}}}".format(outer_nick), nick_value)

    if max_length:
        return nickname_template[:32]

    return nickname_template


