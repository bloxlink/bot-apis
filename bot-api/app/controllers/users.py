"""
Endpoint for user related endpoints
"""

import asyncio
from typing import Optional, Literal, Coroutine

from blacksheep.server.controllers import Controller, get
from blacksheep import FromQuery
from bloxlink_lib import RobloxUser, fetch_roblox_id, fetch_base_data #, use_groups, use_badges
from ..models import Response
from ..binders import FromListQuery


class UserDataResponse(Response):
    user: RobloxUser | None


class UserInfoController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/users"

    @classmethod
    def class_name(cls) -> str:
        return "Roblox User Info Endpoints"
    
    @get("/test")
    async def test(self) -> Response:
        return Response(success=True)

    @get("/")
    async def retrieve_user_info(self, 
                                 username: FromQuery[str] = None,
                                 id: FromQuery[int] = None,
                                 include: FromListQuery = None,
                                 timeout: FromQuery[float] = None
                                 ) -> UserDataResponse | Response:
        """Retrieves the information of the Roblox user."""

        roblox_name: str = username.value if username else None
        roblox_id: int = id.value if id else None
        include: list[str] = include.value if include else None
        timeout: float = timeout.value if timeout else None

        roblox_data: RobloxUser = None

        if not (roblox_name or roblox_id) or (roblox_name and roblox_id):
            return Response(success=False, error="Must provide either a Roblox name or ID")
        
        if not roblox_id:
            # fetch Roblox ID from provided username
            roblox_id = await fetch_roblox_id(roblox_name)

            if not roblox_id:
                return Response(success=False, error="No Roblox user found")
        
        roblox_data = RobloxUser(username=roblox_name, 
                                 id=roblox_id, 
                                 profile_link=f"https://www.roblox.com/users/{roblox_id}/profile")
        
        http_tasks: list[Coroutine] = [
            fetch_base_data(roblox_id),
            # use_avatars()
        ]

        # if "groups" in include or "everything" in include:
        #     http_tasks.append(use_groups())

        # if "badges" in include or "everything" in include:
        #     http_tasks.append(use_badges())

        done, _ = await asyncio.wait([asyncio.create_task(task) for task in http_tasks], timeout=timeout)

        for task in done:
            if task.exception():
                return Response(success=False, error="An error occured while fetching the Roblox user data.")

            for key, value in task.result().items():
                setattr(roblox_data, key, value)

        return UserDataResponse(success=True, user=roblox_data.model_dump(by_alias=True))
