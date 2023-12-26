import asyncio
from os.path import exists
from typing import Callable

from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

from resources.models import GuildData, UserData

# pylint: disable=no-name-in-module
from resources.secrets import (
    MONGO_CA_FILE,
    MONGO_URL,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    REDIS_URL,
)

mongo: AsyncIOMotorClient = None
redis: Redis = None


async def connect_database():
    global mongo
    global redis

    if MONGO_CA_FILE:
        ca_file = exists("cert.crt")

        if not ca_file:
            with open("src/cert.crt", "w") as f:
                f.write(MONGO_CA_FILE)

    mongo = AsyncIOMotorClient(
        MONGO_URL, tlsCAFile="src/cert.crt" if MONGO_CA_FILE else None)
    mongo.get_io_loop = asyncio.get_running_loop

    if REDIS_URL:
        redis = Redis.from_url(REDIS_URL, decode_responses=True)
    else:
        redis = Redis(host=REDIS_HOST, port=REDIS_PORT,
                      password=REDIS_PASSWORD, decode_responses=True)


async def fetch_item(domain: str, constructor: Callable, item_id: str, *aspects) -> object:
    """
    Fetch an item from local cache, then redis, then database.
    Will populate caches for later access
    """
    # should check local cache but for now just fetch from redis

    if aspects:
        item = await redis.hmget(f"{domain}:{item_id}", *aspects)
        item = {x: y for x, y in zip(aspects, item) if y is not None}
    else:
        item = await redis.hgetall(f"{domain}:{item_id}")

    if not item:
        item = await mongo.bloxlink[domain].find_one({"_id": item_id}, {x: True for x in aspects}) or {
            "_id": item_id
        }

        if item and not isinstance(item, (list, dict)):
            if aspects:
                items = {x: item[x] for x in aspects if item.get(
                    x) and not isinstance(item[x], dict)}
                if items:
                    await redis.hset(f"{domain}:{item_id}", items)
            else:
                await redis.hset(f"{domain}:{item_id}", item)

    if item.get("_id"):
        item.pop("_id")

    item["id"] = item_id

    return constructor(**item)


async def update_item(domain: str, item_id: str, **aspects) -> None:
    """
    Update an item's aspects in local cache, redis, and database.
    """
    # update redis cache
    redis_aspects = dict(aspects)

    unset_aspects = {}
    set_aspects = {}
    for key, val in aspects.items():
        if val is None:
            unset_aspects[key] = ""
        else:
            set_aspects[key] = val

    # we don't save lists and dicts to redis
    for aspect_name, aspect_value in dict(aspects).items():
        if isinstance(aspect_value, (dict, list, bool)) or aspect_value is None:
            redis_aspects.pop(aspect_name)

    if redis_aspects:
        await redis.hmset(f"{domain}:{item_id}", redis_aspects)

    # update database
    await mongo.bloxlink[domain].update_one(
        {"_id": item_id}, {"$set": set_aspects, "$unset": unset_aspects}, upsert=True
    )


async def fetch_user_data(user: str | dict, *aspects) -> UserData:
    """
    Fetch a full user from local cache, then redis, then database.
    Will populate caches for later access
    """

    if isinstance(user, dict):
        user_id = str(user["id"])
    else:
        user_id = str(user)

    return await fetch_item("users", UserData, user_id, *aspects)


async def fetch_guild_data(guild: str | dict, *aspects) -> GuildData:
    """
    Fetch a full guild from local cache, then redis, then database.
    Will populate caches for later access
    """

    if isinstance(guild, dict):
        guild_id = str(guild["id"])
    else:
        guild_id = str(guild)

    return await fetch_item("guilds", GuildData, guild_id, *aspects)


async def update_user_data(user: str | dict, **aspects) -> None:
    """
    Update a user's aspects in local cache, redis, and database.
    """

    if isinstance(user, dict):
        user_id = str(user["id"])
    else:
        user_id = str(user)

    return await update_item("users", user_id, **aspects)


async def update_guild_data(guild: str | dict, **aspects) -> None:
    """
    Update a guild's aspects in local cache, redis, and database.
    """

    if isinstance(guild, dict):
        guild_id = str(guild["id"])
    else:
        guild_id = str(guild)

    return await update_item("guilds", guild_id, **aspects)
