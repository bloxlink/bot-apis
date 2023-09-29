import logging
from threading import Lock
import aiohttp
import time
from config import PROXY_AUTH, PROXY_URL
import sentry_sdk
from constants import *
from typing import Optional, Union, Callable, Mapping, Tuple
from utilities.sentry_utils import trace

_session = None
_session_lock = Lock()
def get_session():
    global _session
    with _session_lock:
        if not _session:
            _session = aiohttp.ClientSession()
    return _session

@trace("http.client", lambda *args, **kwargs: f"{args[0]} {args[1]}")
async def fetch(method: str, url, params={}, converter: Optional[Callable[[dict], dict]] = None, headers={}, body=None, replace_data: Optional[dict] = None, **kwargs):
    # """Fetches data from a URL and pastes it into the data dict"""
    params = params or {}
    headers = headers or {}

    if replace_data:
        url = url.format(**replace_data)

    proxy_body = {
        "url": url,
        "method": method,
        "headers": headers or {},
        "data": body or {}
    }

    if not PROXY_URL:
        logging.warning("No proxy was set!")
    else:
        headers["Authorization"] = PROXY_AUTH

    data = None
    async with get_session().request(method="POST" if PROXY_URL else method, url=PROXY_URL if PROXY_URL else url, json=proxy_body if PROXY_URL else body or None, params=params, headers=headers) as resp:
        # if current_span:
        #     current_span.set_http_status(resp.status)
        if resp.status == 200:
            data = await resp.json()
        else:
            print(resp.status, await resp.json())

        if data is not None and converter:
            data = converter(data)

        return data, resp

async def fetch_update(data: dict, method: str, url, params={}, converter: Optional[Callable[[dict], dict]] = None, headers={}, body=None, unwrap_lists=False, replace_data: Optional[dict] = None, **kwargs):
    body, resp = await fetch(method, url, params, converter, headers, body, replace_data, **kwargs)
    if data is None:
        print(url)
    return data.update(body)

@trace()
async def fetch_rolimons(idx, cursor=None, **kwargs):
    # rap = 0
    # params = {
    #     "sortOrder": "Asc",
    #     "limit": 50
    # }

    # body = {
    #     "url": PLACE_VISITS_API.format(id=idx),
    #     "method": "GET",
    #     "data": {}
    # }

    # headers = {
    #     "Authorization": PROXY_AUTH
    # }

    # if cursor:
    #     params["cursor"] = cursor


    # async with get_session().request(method="POST" if PROXY_URL else "GET", url=PROXY_URL if PROXY_URL else PLACE_VISITS_API.format(id=idx), json=body, params=params, headers=headers if PROXY_URL else {}) as resp:
    #     if resp.status != 200:
    #         data["placeVisits"] = None
    #         return

    #     if data.get("placeVisits") is None:
    #         data["placeVisits"] = 0

    #     json = await resp.json()

    #     for place in json.get("data", []):
    #         if place.get("placeVisits"):
    #             place_visits += place["placeVisits"]

    #     if json.get("nextPageCursor"):
    #         await fetch_place_visis(idx, data, cursor=json.get("nextPageCursor"))

    # if place_visits:
    #     if data["placeVisits"] is None:
    #         data["placeVisits"] = 0

    #     data["rap"] += rap

    stats_updated = None

    cached_data, response = await fetch("GET", ROLIMON_APIS["PLAYER_DATA"], replace_data={"id":idx})

    if response.status == 200:
        stats_updated = cached_data["last_scan"]

        if stats_updated and stats_updated + SECONDS_IN_A_WEEK >= time.time(): # + 604800:
            return cached_data.get("value", cached_data.get("rap")) or 0

    elif response.status == 422:
        # player is missing from database, so add them
        _, response_add_player = await fetch("GET", ROLIMON_APIS["ADD_PLAYER"], replace_data={"id":idx})

        if response_add_player.status != 200:
            return

    else:
        return

    # scan inventory and fetch again
    _, response_scan = await fetch("GET", ROLIMON_APIS["SCAN_INVENTORY"], replace_data={"id":idx})

    if response_scan.status == 200:
        cached_data, response = await fetch("GET", ROLIMON_APIS["PLAYER_DATA"], replace_data={"id":idx})

        if response.status == 200:
            return cached_data.get("value", cached_data.get("rap")) or 0


@trace()
async def fetch_place_visits(idx, cursor=None, **kwargs) -> int | None:
    place_visits = 0
    params = {
        "sortOrder": "Asc",
        "limit": 50
    }

    body = {
        "url": PLACE_VISITS_API.format(id=idx),
        "method": "GET",
        "data": {}
    }

    if cursor:
        params["cursor"] = cursor

    data, resp = await fetch("GET", PLACE_VISITS_API, json=body, params=params, replace_data={"id":idx})
    for place in data.get("data", []):
        if place.get("placeVisits"):
            place_visits += place["placeVisits"]

        if data.get("nextPageCursor"):
            place_visits += await fetch_place_visits(idx, cursor=data.get("nextPageCursor"))

    return place_visits
