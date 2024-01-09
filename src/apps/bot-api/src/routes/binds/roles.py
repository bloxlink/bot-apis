from sanic.response import json

from resources.binds import GroupBind, GuildBind, get_binds
from resources.database import fetch_guild_data
from resources.models import GuildData


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
        if not guild_id:
            return json({"success": False, "reason": "No guild_id was given."})

        response = await calculate_final_roles(json_data, guild_id)

        return json({"success": True, **response})


async def calculate_final_roles(data: dict, guild_id: str) -> dict:
    final_roles: list = data.get("user_roles", [])
    final_roles = [str(x) for x in final_roles]
    original_roles = set(final_roles)

    successful_binds: dict = data.get("successful_binds", {"give": [], "remove": []})

    guild_data: GuildData = await fetch_guild_data(guild_id, "allowOldRoles")
    guild_data.binds = await get_binds(guild_id)

    guild_binds: list = guild_data.binds or []
    allow_old_roles = guild_data.allowOldRoles

    # Get all the roles that are related to a bind in some way.
    # This does not include the default verified/unverified roles.
    # TODO: Include entire group binds.
    bind_related_roles = set()
    entire_group_binds = []

    for bind in guild_binds:
        bind: GuildBind

        if bind is GroupBind:
            if bind.subtype == "linked_group":
                entire_group_binds.append(bind)

        bind_related_roles.update(bind.roles)
        bind_related_roles.update(bind.removeRoles)

    # Update final_roles so that way we just have the roles of a user that
    # we should not change if allowOldRoles is disabled.
    if not allow_old_roles:
        non_bind_roles = set(final_roles).difference(bind_related_roles)
        final_roles = list(non_bind_roles)

    final_roles = set(final_roles)

    # Stringify in case a mismatch somehow occurs.
    # final_roles and original_roles are stringified by this point.
    roles_to_give = set([str(x) for x in successful_binds["give"]])
    roles_to_remove = set([str(x) for x in successful_binds["remove"]])

    # Remove roles that will be removed from the roles being given since it's redundant.
    roles_to_give.difference_update(roles_to_remove)

    # Figure out which roles were added (compared to original roles) & update final_roles.
    final_given_roles = roles_to_give.difference(original_roles)
    final_roles.update(roles_to_give)

    # Figure out which roles were removed (compared to original_roles) & update final_roles.
    final_removed_roles = roles_to_remove.intersection(original_roles)
    final_roles.difference_update(roles_to_remove)

    return {
        "final_roles": list(final_roles),
        "added_roles": list(final_given_roles),
        "removed_roles": list(final_removed_roles),
    }
