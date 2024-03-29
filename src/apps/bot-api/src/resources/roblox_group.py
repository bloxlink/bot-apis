import re

from attrs import define

from resources.exceptions import RobloxAPIError, RobloxNotFound
from resources.utils import fetch

GROUP_API = "https://groups.roblox.com/v1/groups"
ROBLOX_GROUP_REGEX = re.compile(r"roblox.com/groups/(\d+)/")


@define(slots=True)
class RobloxGroup:
    """Representation of a Group on Roblox.


    Attributes:
        member_count (int): Number of members in this group. None by default.
        rolesets (dict[int, str], optional): Rolesets of this group, by {roleset_id: roleset_name}. None by default.
        user_roleset (dict): The roleset of a specific user in this group. Used for applying binds.

    This is in addition to attributes provided by RobloxEntity.
    """

    id: str
    name: str = None
    description: str = None
    synced: bool = False
    url: str = None

    member_count: int = None
    rolesets: dict[int, str] = None
    user_roleset: dict = None

    def __attrs_post_init__(self):
        self.url = f"https://www.roblox.com/groups/{self.id}"

    async def sync(self):
        """Retrieve the roblox group information, consisting of rolesets, name, description, and member count."""
        if self.synced:
            return

        if self.rolesets is None:
            json_data, _ = await fetch(f"{GROUP_API}/{self.id}/roles", "GET")

            self.rolesets = {int(roleset["rank"]): roleset["name"].strip(
            ) for roleset in json_data["roles"]}

        if self.name is None or self.description is None or self.member_count is None:
            json_data, _ = await fetch(f"{GROUP_API}/{self.id}", "GET")

            self.name = json_data.get("name")
            self.description = json_data.get("description")
            self.member_count = json_data.get("memberCount")

            if self.rolesets is not None:
                self.synced = True

    def __str__(self) -> str:
        name = f"**{self.name}**" if self.name else "*(Unknown Group)*"
        return f"{name} ({self.id})"

    def roleset_name_string(self, roleset_id: int, bold_name=True, include_id=True) -> str:
        """Generate a nice string for a roleset name with failsafe capabilities.

        Args:
            roleset_id (int): ID of the Roblox roleset.
            bold_name (bool, optional): Wraps the name in ** when True. Defaults to True.
            include_id (bool, optional): Includes the ID in parenthesis when True. Defaults to True.

        Returns:
            str: The roleset string as requested.
        """
        roleset_name = self.rolesets.get(roleset_id, "")
        if not roleset_name:
            return str(roleset_id)

        if bold_name:
            roleset_name = f"**{roleset_name}**"

        return f"{roleset_name} ({roleset_id})" if include_id else roleset_name

    async def rolesets_to_roles(self, roles: list) -> dict:
        role_output = {}

        if not self.synced:
            await self.sync()

        for role in roles:
            if role["managed"]:
                continue

            for roleset_name in self.rolesets.values():
                if role["name"] == roleset_name:
                    role_output[roleset_name] = role["id"]

        return role_output


async def get_group(group_id_or_url: str | int) -> RobloxGroup:
    """Get and sync a RobloxGroup.

    Args:
        group_id_or_url (str): ID or URL of the group to retrieve

    Raises:
        RobloxNotFound: Raises RobloxNotFound when the Roblox API has an error.

    Returns:
        RobloxGroup: A synced roblox group.
    """

    group_id_or_url = str(group_id_or_url)
    regex_search = ROBLOX_GROUP_REGEX.search(group_id_or_url)

    if regex_search:
        group_id = regex_search.group(1)
    else:
        group_id = group_id_or_url

    group: RobloxGroup = RobloxGroup(id=group_id)

    try:
        await group.sync()  # this will raise if the group doesn't exist
    except RobloxAPIError as exc:
        raise RobloxNotFound("This group does not exist.") from exc

    return group
