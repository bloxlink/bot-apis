import copy

from sanic.response import json

from resources.binds import GroupBind, GuildBind, get_binds
from resources.database import fetch_guild_data
from resources.models import GuildData
from resources.roblox_group import RobloxGroup


class Route:
    """Calculate what roles a user should or should not have."""

    PATH = "/binds/roles/"
    METHODS = ("POST",)
    NAME = "user_role_calculation"

    async def handler(self, request):
        """Handle the /binds/roles/ endpoint.

        Determines what roles a user should have based on the bindings that
        apply to them.

        Restricted users will always result in the unverified role(s) being
        returned.

        The payload of the request should contain:
        - The guild ID
        - A list of the user's current roles (IDs only)
        - The roles to be given & removed based on the user's bindings

        Example payload:
        {
            "guild_id": "1234567",
            "user_roles": ["12345"],
            "successful_binds": {"give": ["1234"], "remove": ["12344"]},
        }

        Based on the output from /binds/<user_id>, the Unverified & Verified role IDs will
        already be included in the successful_binds section, along with the entire group binds.

        Likewise, restricted logic should have already been handled prior, so the unverified role is expected
        to be the only binding to give.

        Returns:
            A JSON payload that determines if the request was successful or not, and what roles
            were added, which were removed, and the resulting role list.

            Example successful response:
            {
                "success": true
                "final_roles": ["123456", "12346782134698"],
                "added_roles": ["123456"],
                "removed_roles": ["123487578"],
            }

            Example failure response:
            {
                "success": false
                "reason": (str),
            }
        """

        json_data: dict = request.json or {}

        guild_id: str = json_data.get("guild_id")
        guild_roles: list = json_data.get("guild_roles")
        if not guild_id:
            return json({"success": False, "reason": "No guild_id was given."})
        if not guild_roles:
            return json({"success": False, "reason": "No guild_roles were given."})

        response = await calculate_final_roles(json_data, guild_id, guild_roles)

        return json({"success": True, **response})


async def calculate_final_roles(data: dict, guild_id: str, guild_roles: list) -> dict:
    final_roles: list = data.get("user_roles", [])
    final_roles = set(str(x) for x in final_roles)
    original_roles: set = copy.copy(final_roles)

    successful_binds: dict = data.get("successful_binds", {"give": [], "remove": []})

    guild_data: GuildData = await fetch_guild_data(guild_id, "allowOldRoles")
    guild_data.binds = await get_binds(guild_id)

    # Get all the roles that are related to a bind in some way.
    # This does not include the default verified/unverified roles.
    bind_related_roles = set()
    linked_group_roles = set()

    for bind in guild_data.binds:
        bind: GuildBind

        if isinstance(bind, GroupBind):
            if bind.subtype == "linked_group":
                group = RobloxGroup(bind.id)
                matched_roles = await group.rolesets_to_roles(guild_roles)

                linked_group_roles.update([str(value) for value in matched_roles.values()])

        if bind.roles:
            bind_related_roles.update(str(x) for x in bind.roles)
        if bind.removeRoles:
            bind_related_roles.update(str(x) for x in bind.removeRoles)

    # Stringify in case a mismatch somehow occurs.
    roles_to_give = set(str(x) for x in successful_binds["give"])
    roles_to_remove = set(str(x) for x in successful_binds["remove"])

    # Update final_roles so that way we just have the roles of a user that
    # we should not change if allowOldRoles is disabled.
    if not guild_data.allowOldRoles:
        final_roles.difference_update(bind_related_roles, linked_group_roles)

        # Add entire group-related roles to list of roles to remove.
        linked_group_roles.difference_update(roles_to_give)
        linked_group_roles.intersection_update(original_roles)
        roles_to_remove.update(linked_group_roles)

    # Remove roles that will be removed from the roles being given since it's redundant.
    roles_to_give.difference_update(roles_to_remove)

    # Figure out which roles were added (compared to original roles) & update final_roles.
    final_given_roles = roles_to_give.difference(original_roles)
    final_roles.update(roles_to_give)

    # Figure out which roles were removed (compared to original_roles) & update final_roles.
    final_roles.difference_update(roles_to_remove)
    final_removed_roles = original_roles.difference(final_roles)

    return {
        "final_roles": list(final_roles),
        "added_roles": list(final_given_roles),
        "removed_roles": list(final_removed_roles),
    }
