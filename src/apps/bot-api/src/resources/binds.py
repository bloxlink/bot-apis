from typing import Literal

from attrs import define

from resources.database import fetch_guild_data, update_guild_data
from resources.exceptions import BloxlinkException
from resources.models import GuildData, default_field

POP_OLD_BINDS: bool = False

ValidBindType = Literal["group", "asset", "badge", "gamepass", "verified", "unverified"]


@define(slots=True)
class GuildBind:
    """Represents a binding from the database.

    Post init it should be expected that the id, type, and entity types are not None.

    Attributes:
        nickname (str, optional): The nickname template to be applied to users. Defaults to None.
        roles (list): The IDs of roles that should be given by this bind.
        removeRole (list): The IDs of roles that should be removed when this bind is given.

        id (int, optional): The ID of the entity for this binding. Defaults to None.
        type (ValidBindType): The type of binding this is representing.
        bind (dict): The raw data that the database stores for this binding.

        entity (RobloxEntity, optional): The entity that this binding represents. Defaults to None.
    """

    nickname: str = None
    roles: list = default_field(list())
    removeRoles: list = default_field(list())

    id: int = None
    type: ValidBindType = ValidBindType
    bind: dict = default_field({"type": "", "id": None})

    def __attrs_post_init__(self):
        # pylint: disable=E1101
        self.id = self.bind.get("id")
        self.type = self.bind.get("type")
        # pylint: enable=E1101

    def to_dict(self) -> dict:
        return {
            "roles": self.roles,
            "removeRoles": self.removeRoles,
            "nickname": self.nickname,
            "bind": {"type": self.type, "id": self.id},
        }


class GroupBind(GuildBind):
    """Represents additional attributes that only apply to group binds.

    Except for min and max (which are used for ranges), only one attribute should be considered to be
    not None at a time.

    Attributes:
        min (int, optional): The minimum rank that this bind applies to. Defaults to None.
        max (int, optional): The maximum rank that this bind applies to. Defaults to None.
        roleset (int, optional): The specific rank that this bind applies to. Defaults to None.
            Can be negative (in legacy format) to signify that specific rank and higher.
        everyone (bool, optional): Does this bind apply to everyone. Defaults to None.
        guest (bool, optional): Does this bind apply to guests. Defaults to None.
    """

    min: int = None
    max: int = None
    roleset: int = None
    everyone: bool = None
    guest: bool = None

    def __attrs_post_init__(self):
        # pylint: disable=E1101
        self.min = self.bind.get("min", None)
        self.max = self.bind.get("max", None)
        self.roleset = self.bind.get("roleset", None)
        self.everyone = self.bind.get("everyone", None)
        self.guest = self.bind.get("guest", None)
        # pylint: enable=E1101

        return super().__attrs_post_init__()

    @property
    def subtype(self) -> str:
        """The specific type of this group bind.

        Returns:
            str: "linked_group" or "group_roles" depending on if there
                are roles explicitly listed to be given or not.
        """
        if not self.roles or self.roles in ("undefined", "null"):
            return "linked_group"
        else:
            return "group_roles"

    def to_dict(self) -> dict:
        base_dict = super().to_dict()

        if self.roleset is not None:
            base_dict["bind"]["roleset"] = self.roleset

        if self.min is not None:
            base_dict["bind"]["min"] = self.min

        if self.max is not None:
            base_dict["bind"]["max"] = self.max

        if self.guest is not None and self.guest:
            base_dict["bind"]["guest"] = self.guest

        if self.everyone is not None and self.everyone:
            base_dict["bind"]["everyone"] = self.everyone

        return base_dict


async def get_binds(guild_id: int | str) -> list[GuildBind]:
    """Get the current guild binds.

    Old binds will be included by default, but will not be saved in the database in the
    new format unless the POP_OLD_BINDS flag is set to True. While it is False, old formatted binds will
    be left as is.
    """

    guild_id = str(guild_id)
    guild_data: GuildData = await fetch_guild_data(
        guild_id, "binds", "groupIDs", "roleBinds", "converted_binds"
    )

    # Convert and save old bindings in the new format
    if not guild_data.converted_binds and (
        guild_data.groupIDs is not None or guild_data.roleBinds is not None
    ):
        old_binds = []

        if guild_data.groupIDs:
            old_binds.extend(convert_v3_binds_to_v4(guild_data.groupIDs, "group"))

        if guild_data.roleBinds:
            gamepasses = guild_data.roleBinds.get("gamePasses")
            if gamepasses:
                old_binds.extend(convert_v3_binds_to_v4(gamepasses, "gamepass"))

            assets = guild_data.roleBinds.get("assets")
            if assets:
                old_binds.extend(convert_v3_binds_to_v4(assets, "asset"))

            badges = guild_data.roleBinds.get("badges")
            if badges:
                old_binds.extend(convert_v3_binds_to_v4(badges, "badge"))

            group_ranks = guild_data.roleBinds.get("groups")
            if group_ranks:
                old_binds.extend(convert_v3_binds_to_v4(group_ranks, "group"))

        if old_binds:
            # Prevent duplicates from being made. Can't use sets because dicts aren't hashable
            guild_data.binds.extend(bind for bind in old_binds if bind not in guild_data.binds)

            await update_guild_data(guild_id, binds=guild_data.binds, converted_binds=True)
            guild_data.converted_binds = True

    if POP_OLD_BINDS and guild_data.converted_binds:
        await update_guild_data(guild_id, groupIDs=None, roleBinds=None, converted_binds=None)

    return json_binds_to_guild_binds(guild_data.binds)


def convert_v3_binds_to_v4(items: dict, bind_type: str) -> list:
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


def json_binds_to_guild_binds(bind_list: list) -> list:
    """Convert a bind from a dict/json representation to a GuildBind or GroupBind object.

    Args:
        bind_list (list): List of bindings to convert
        category (ValidBindType, optional): Category to filter the binds by. Defaults to None.
        id_filter (str, optional): ID to filter the binds by. Defaults to None.
            Applied after the category if both are given.

    Raises:
        BloxlinkException: When no matching bind type is found from the json input.

    Returns:
        list: The list of bindings as GroupBinds or GuildBinds, filtered by the category & id.
    """
    binds = []

    for bind in bind_list:
        bind_data = bind.get("bind")
        bind_type = bind_data.get("type")

        if bind_type == "group":
            classed_bind = GroupBind(**bind)
        elif bind_type:
            classed_bind = GuildBind(**bind)
        else:
            raise BloxlinkException("Invalid bind structure found.")

        binds.append(classed_bind)

    bind_list.sort(key=lambda e: e.bind["id"])
    return bind_list
