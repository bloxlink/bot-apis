from resources.database import fetch_guild_data, update_guild_data, mongo
from resources.models import GuildData

async def get_binds(guild_id: int | str) -> list[dict]:
    """Get the current guild binds.

    Old binds will be included by default, but will not be saved in the database in the
    new format unless the POP_OLD_BINDS flag is set to True. While it is False, old formatted binds will
    be left as is.
    """

    guild_id = str(guild_id)
    guild_data: GuildData = await fetch_guild_data(guild_id, "binds", "groupIDs", "roleBinds")

    # Set to True to remove the old bind fields from the database (groupIDs and roleBinds)
    POP_OLD_BINDS: bool = False

    # Convert and save old bindings in the new format (only if no new binds exist already).
    # Should be safe to presume this because the new format should not exist for people yet.
    if not guild_data.binds:
        old_binds = []

        if guild_data.groupIDs:
            old_binds.extend(convert_old_binds(guild_data.groupIDs, "group"))

        if guild_data.roleBinds:
            gamepasses = guild_data.roleBinds.get("gamePasses")
            if gamepasses:
                old_binds.extend(convert_old_binds(gamepasses, "gamepass"))

            assets = guild_data.roleBinds.get("assets")
            if assets:
                old_binds.extend(convert_old_binds(assets, "asset"))

            badges = guild_data.roleBinds.get("badges")
            if badges:
                old_binds.extend(convert_old_binds(badges, "badge"))

            group_ranks = guild_data.roleBinds.get("groups")
            if group_ranks:
                old_binds.extend(convert_old_binds(group_ranks, "group"))

        # Save old bindings in the new format if any.
        if old_binds:
            guild_data.binds = old_binds
            await update_guild_data(guild_id, binds=guild_data.binds)

    if POP_OLD_BINDS and (guild_data.groupIDs or guild_data.roleBinds):
        # TODO: Update redis cache? Invalidate old guild data entry?
        await mongo.bloxlink["guilds"].update_one(
            {"_id": guild_id}, {"$unset": {"groupIDs": "", "roleBinds": ""}}
        )

    return guild_data.binds


def convert_old_binds(items: dict, bind_type: str) -> list:
    """Convert old bindings to the new bind format.

    Args:
        items (dict): The bindings to convert.
        bind_type (ValidBindType): Type of bind that is being made.

    Returns:
        list: The binds in the new format.
    """
    output = []

    for bind_id, data in items.items():
        group_rank_binding = data.get("binds") or data.get("ranges")

        if bind_type != "group" or not group_rank_binding:
            bind_data = {
                "roles": data.get("roles"),
                "removeRoles": data.get("removeRoles"),
                "nickname": data.get("nickname"),
                "bind": {"type": bind_type, "id": int(bind_id)},
            }
            output.append(bind_data)
            continue

        # group rank bindings
        if data.get("binds"):
            for rank_id, sub_data in data["binds"].items():
                bind_data = {}

                bind_data["bind"] = {"type": bind_type, "id": int(bind_id)}
                bind_data["roles"] = sub_data.get("roles")
                bind_data["nickname"] = sub_data.get("nickname")
                bind_data["removeRoles"] = sub_data.get("removeRoles")

                # Convert to an int if possible beforehand.
                try:
                    rank_id = int(rank_id)
                except ValueError:
                    pass

                if rank_id == "all":
                    bind_data["bind"]["everyone"] = True
                elif rank_id == 0:
                    bind_data["bind"]["guest"] = True
                elif rank_id < 0:
                    bind_data["bind"]["min"] = abs(rank_id)
                else:
                    bind_data["bind"]["roleset"] = rank_id

                output.append(bind_data)

        # group rank ranges
        if data.get("ranges"):
            for range_item in data["ranges"]:
                bind_data = {}

                bind_data["bind"] = {"type": bind_type, "id": int(bind_id)}
                bind_data["roles"] = range_item.get("roles")
                bind_data["nickname"] = range_item.get("nickname")
                bind_data["removeRoles"] = range_item.get("removeRoles")

                bind_data["bind"]["min"] = int(range_item.get("low"))
                bind_data["bind"]["max"] = int(range_item.get("high"))

                output.append(bind_data)

    return output
