import re

from sanic.response import json

from resources.constants import DEFAULTS
from resources.database import fetch_guild_data
from resources.models import GuildData

nickname_template_regex = re.compile(r"\{(.*?)\}")
any_group_nickname = re.compile(r"\{group-rank-(.*?)\}")


class Route:
    PATH = "/nickname/parse/"
    METHODS = ("GET",)
    NAME = "user_nickname"

    async def handler(self, request):
        json_body = request.json or {}

        # Uncompleted Templates:
        #   X-{roblox-join-date} (Commented out in bloxlink-http)

        # Discord/Guilded user data
        # Expected data is a dict w/ the vals: "name", "nick", & "id"
        user_data = json_body.get("user_data")

        # Only need a guild id and a guild name for guild-related data.
        guild_id = json_body.get("guild_id")
        guild_name = json_body.get("guild_name")

        # Roblox account data (name, id, displayName, description, groups, groupsv2, etc...)
        roblox_account = json_body.get("roblox_account")

        # The nickname template sent to this api endpoint for processing, defaults to {smart-name}
        template = json_body.get("template") or DEFAULTS.get("nicknameTemplate") or ""

        # Determines if result should be limited to 32 characters or not
        is_nickname = json_body.get("is_nickname")
        if is_nickname is None:
            is_nickname = True

        # Group placeholder values
        group_data = roblox_account.get("groupsv2")
        group_id = json_body.get("group_id")

        if template == "{disable-nicknaming}":
            return json({"success": True, "nickname": None})

        is_restricted = json_body.get("restricted", False)

        if roblox_account and not is_restricted:
            roblox_username = roblox_account.get("name")
            roblox_display_name = roblox_account.get("displayName")

            if not group_id:
                guild_data: GuildData = await fetch_guild_data(str(guild_id), "binds")
                group_id = next(
                    (
                        b.get("bind").get("id")
                        for b in guild_data.binds
                        if guild_data.binds and b["bind"]["type"] == "group"
                    ),
                    None,
                )

            linked_group = roblox_account.get("groupsv2").get(str(group_id)) if group_id else None
            group_rank = linked_group.get("role").get("name") if linked_group else "Guest"

            smart_name = ""
            if "smart-name" in template:
                smart_name = f"{roblox_display_name} (@{roblox_username})"

                if roblox_username == roblox_display_name or len(smart_name) > 32:
                    smart_name = roblox_username

            # Handles {group-rank-<ID>}
            for multi_group_id in any_group_nickname.findall(template):
                current_group = group_data.get(multi_group_id)
                multi_group_role = current_group.get("role").get("name") if current_group else "Guest"

                template = template.replace(f"group-rank-{multi_group_id}", multi_group_role)

            template = (
                template.replace("roblox-name", str(roblox_username))
                .replace("display-name", str(roblox_display_name))
                .replace("smart-name", str(smart_name))
                .replace("roblox-id", str(roblox_account.get("id")))
                .replace("roblox-age", str(roblox_account.get("age_days")))
                .replace("group-rank", str(group_rank))
            )
        else:
            # Unverified &/or restricted users
            if not template:
                template: str | None = (
                    await fetch_guild_data(str(guild_id), "unverifiedNickname")
                ).unverifiedNickname

            if template == "{disable-nicknaming}":
                return json({"success": True, "nickname": None})

        template = (
            template.replace("discord-name", str(user_data.get("name")))
            .replace("discord-nick", str(user_data.get("nick")))
            .replace("discord-mention", f"<@{user_data.get('id')}>")
            .replace("discord-id", str(user_data.get("id")))
            .replace("guilded-name", str(user_data.get("name")))
            .replace("guilded-nick", str(user_data.get("nick")))
            .replace("guilded-mention", f"@{user_data.get('name')}")
            .replace("guilded-id", str(user_data.get("id")))
            .replace("group-url", f"https://www.roblox.com/groups/{group_id}" if group_id else "")
            .replace("group-name", str(linked_group.get("group").get("name")) if linked_group else "")
            .replace("prefix", "/")
            .replace("server-name", str(guild_name))
        )

        template = self.parse_capitalization(template)

        return json({"success": True, "nickname": template[:32] if is_nickname else template})

    def parse_capitalization(self, template: str) -> str:
        for outer_nick in nickname_template_regex.findall(template):
            nick_data = outer_nick.split(":")
            nick_fn = None
            nick_value = None

            if len(nick_data) > 1:
                nick_fn = nick_data[0]
                nick_value = nick_data[1]
            else:
                nick_value = nick_data[0]

            # nick_fn = capA
            # nick_value = roblox-name

            if nick_fn:
                if nick_fn in ("allC", "allL"):
                    if nick_fn == "allC":
                        nick_value = nick_value.upper()
                    elif nick_fn == "allL":
                        nick_value = nick_value.lower()

                    template = template.replace("{{{0}}}".format(outer_nick), nick_value)
                else:
                    template = template.replace("{{{0}}}".format(outer_nick), outer_nick)  # remove {} only
            else:
                template = template.replace("{{{0}}}".format(outer_nick), nick_value)
            pass

        return template
