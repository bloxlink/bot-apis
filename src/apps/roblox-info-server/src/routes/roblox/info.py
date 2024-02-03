import inspect
from typing import Callable, Optional
from sanic.response import json
from config import DEFAULT_TIMEOUT
import asyncio
from resources.fetch import *
import sentry_sdk
from sentry_sdk.tracing import Span, NoOpSpan
from sentry_sdk.utils import qualname_from_function


class Route:
    PATH = "/roblox/info/"
    METHODS = ("GET", )

    async def handler(self, request):
        included_sentry_trace_id = request.headers.get("sentry_trace_id", None)

        # TODO: Move to middleware / request execution handler.
        with sentry_sdk.start_transaction(op="task", name=f"/roblox/info", trace_id=included_sentry_trace_id) as trans:
            idx: str | None = request.args.get("id")
            username: str | None = request.args.get("username")
            include = request.args.get("include", "").split(",") or ["everything"] # groups, avatar, badges
            timeout: int = int(request.args.get("timeout")) if request.args.get("timeout") is not None else DEFAULT_TIMEOUT
            resolve_avatars: bool = request.args.get("resolveAvatars") == "true"

            sentry_sdk.set_user({
                "id": idx
            })

            # auth = request.headers.get("Authorization")

            # if not auth:
            #     return json({
            #         "error": "No API key provided",
            #         "success": False
            #     }, 401)

            # if auth != INFO_AUTH:
            #     if not proxy_endpoint:
            #         return json({
            #             "error": "Invalid API key",
            #             "success": False
            #         }, 401)

            if not (idx or username):
                if trans:
                    trans.status = "invalid_argument"
                return json({
                    "error": "No ID or username provided",
                    "success": False
                }, 400)

            data = {
                "name": None,
                "id": None,
                "displayName": None,
                "description": None,
                "isBanned": None,
                "created": None,
                "badges": None,
                "profileLink": None,
                "presence": None,
                "groups": None,
                "avatar": None,
                "rap": None,
                "value": None,
                "placeVisits": None,
                "hasDisplayName": None,
                "avatar": {}
            }

            # -- We need async lambdas! :angry: --
            async def use_groups():
                json, resp = await fetch("GET", USER_GROUPS, replace_data={"id": idx}, converter=lambda x: x["data"], parent_span=trans)
                data["groups"] = {}

                for group_data in json:
                    data["groups"][int(group_data["group"]["id"])] = group_data

            async def use_avatars():
                for avatar_name, avatar_url in AVATAR_URLS.items():
                    avatar_value = None

                    if resolve_avatars:
                        json, resp = await fetch("GET", avatar_url, replace_data={"id": idx}, converter=lambda x: x["data"][0]["imageUrl"], parent_span=trans)
                        avatar_value = json
                    else:
                        avatar_value = avatar_url.format(id=idx)

                    data["avatar"][avatar_name] = avatar_value

            async def use_badges():
                json, resp = await fetch("GET", USER_BADGES, replace_data={"id": idx}, converter=lambda x: x["RobloxBadges"], parent_span=trans)
                data["badges"] = json

            async def use_value():
                value = await fetch_rolimons(idx, parent_span=trans)
                data["value"] = value
                data["rap"] = value
                # NOTE: Both are set for backwards usage.

            async def use_place_visits():
                visits = await fetch_place_visits(idx, parent_span=trans)
                data["placeVisits"] = visits

            if not idx and username:
                # fetch id from provided username
                response_data, _ = await fetch("POST", f"{USERS_API}/v1/usernames/users", body={
                    "usernames": [
                        username
                    ],
                    "excludeBannedUsers": False
                }, parent_span=trans)
                idx = response_data["data"][0]["id"] if len(response_data["data"]) else None

                if not idx:
                    if trans:
                        trans.status = "not_found"
                    return json({
                        "error": "No user was found with this username",
                        "success": False
                    }, 404)

            data["profileLink"] = PROFILE_URL.format(id=idx)

            http_tasks = [
                fetch_update(data, "GET", BASE_DATA, replace_data={"id": idx}, parent_span=trans), # retrieve base data
                use_avatars()
            ]

            if "groups" in include or "everything" in include:
                http_tasks.append(use_groups())

            if "badges" in include or "everything" in include:
                http_tasks.append(use_badges())

            # if "value" in include or "everything" in include:
            #     http_tasks.append(use_value())

            # if "placeVisits" in include or "everything" in include:
            #     http_tasks.append(use_place_visits())

            await asyncio.wait(http_tasks, timeout=timeout)

            data["hasDisplayName"] = data["name"] != data["displayName"]

            if not (data["name"] and data["id"]):
                if trans:
                    trans.status = "not_found"
                return json({
                    "error": "No user was found.",
                    "success": False
                }, 404)

            sentry_sdk.set_user({
                "id": idx,
                "username": data["name"]
            })

            if trans:
                trans.status = "ok"

            return json(data)
