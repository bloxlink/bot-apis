from typing import Iterable, Optional
from discord import Role, User, Member, Guild, Asset, TextChannel, CategoryChannel, VoiceChannel, Emoji
from discord.utils import SequenceProxy
from enum import Enum
from requests.utils import requote_uri

import aiohttp, asyncio
import inspect
import datetime
import json

session = None


def find(predicate, items: Iterable):
    """Returns the first item that suffices the predicate."""
    if not inspect.isfunction(predicate):
        raise TypeError("Predicate must be a function.")

    for item in items:
        if predicate(item):
            return item
    return False


def filter_dict(value: dict, *fields: str):
    if len(fields) == 0:
        return value

    new_dict = {}
    for field in fields:
        new_dict[field] = value[field]
    return new_dict


class MinimalConversions:
    """A set of conversion methods to use when responding with Discord objects."""

    @staticmethod
    def convert(input: object, filter: Optional[list[str]]):
        """Automatically generates a dictionary of attributes for an object."""
        dir_dict = {}
        # Get all possible values if there's no filter, else get what is filtered.
        input_dir = dir(input) if not filter else list(set(dir(input)) & set(filter))

        for ele in input_dir:
            # Ignore "private" fields.
            if ele.startswith("_"):
                continue

            # Ignore methods which proceed with <bound
            attr = getattr(input, ele)
            if str(attr).startswith("<bound ") or str(attr).startswith("<built-in method"):
                continue

            attr_type = type(attr)

            if attr_type in (Guild, TextChannel, CategoryChannel, VoiceChannel):
                dir_dict[ele] = attr.id

            elif attr_type is Asset:
                dir_dict[ele] = MinimalConversions.convert_asset(attr)

            elif attr_type is User:
                dir_dict[ele] = MinimalConversions.convert_user(attr)

            elif attr_type is Role:
                dir_dict[ele] = MinimalConversions.convert_role(attr)

            elif attr_type is Member:
                dir_dict[ele] = MinimalConversions.convert_member(attr)

            elif attr_type is Emoji:
                dir_dict[ele] = dict(attr)

            elif attr_type is datetime.datetime:
                dir_dict[ele] = attr.isoformat()

            elif attr_type is list or attr_type is tuple or attr_type is SequenceProxy:
                sub_list = []
                for n in attr:
                    try:
                        sub_list.append(n.id)
                    except:
                        sub_list.append(n)
                dir_dict[ele] = sub_list
            else:
                try:
                    dir_dict[ele] = attr.value
                except:
                    dir_dict[ele] = attr

        return dir_dict

    @staticmethod
    def convert_asset(asset: Optional[Asset]) -> str | None:
        return asset._url if asset else None

    @staticmethod
    def convert_user(user: User) -> dict:
        return {
            "id": user.id,
            "name": user.name,
            "discriminator": user.discriminator,
            "avatar_url": MinimalConversions.convert_asset(user.avatar),
            "is_bot": user.bot,
            "created_at": user.created_at.strftime("%Y-%m-%d"),
        }

    @staticmethod
    def convert_channel(channel):
        return {
            "id": channel.id,
            "name": channel.name,
            "position": channel.position,
            "type": channel.type.value,
        }

    @staticmethod
    def convert_role(role: Role):
        return {
            "id": role.id,
            "name": role.name,
            "color": role.color.to_rgb(),
            "is_managed": role.is_bot_managed(),
            "is_premium_subscriber": role.is_premium_subscriber(),
            "is_integration": role.is_integration(),
            "permissions": role.permissions.value,
        }

    @staticmethod
    def convert_member(member: Member):
        result = {
            "activity": member.activity,
            # "color": member.color,
            "nickname": member.nick,
            "guild_id": member.guild.id,
            "guild_avatar": MinimalConversions.convert_asset(member.guild_avatar),
            "permissions": member.guild_permissions.value,
            "joined_at": member.joined_at.strftime("%Y-%m-%d") if member.joined_at is not None else "",
            "roles": [r.id for r in member.roles],
            "is_owner": member.id == member.guild.owner_id,
        }
        result.update(MinimalConversions.convert_user(member._user))
        return result


class ReturnType(Enum):
    JSON = 1
    TEXT = 2
    BYTES = 3


async def fetch(
    method: str,
    url: str,
    params: dict = None,
    headers: dict = None,
    body: dict = {},
    return_data: ReturnType = ReturnType.JSON,
    timeout: float = 20,
):
    params = params or {}
    headers = headers or {}

    global session

    if not session:
        session = aiohttp.ClientSession()

    url = requote_uri(url)

    for k, v in params.items():
        if isinstance(v, bool):
            params[k] = "true" if v else "false"

    try:
        async with session.request(
            method,
            url,
            json=body,
            params=params,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout) if timeout else None,
        ) as response:
            if return_data is ReturnType.TEXT:
                text = await response.text()
                return text, response

            elif return_data is ReturnType.JSON:
                try:
                    json = await response.json()
                except aiohttp.client_exceptions.ContentTypeError as ex:
                    print(url, await response.text(), flush=True)
                    raise ex

                return json, response

            elif return_data is ReturnType.BYTES:
                return await response.read(), response

            return response

    except asyncio.TimeoutError as ex:
        print(f"URL {url} timed out", flush=True)
        raise ex
