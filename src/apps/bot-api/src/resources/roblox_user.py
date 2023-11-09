from typing import Literal

import resources.utils as utils
from resources.exceptions import RobloxAPIError

INVENTORY_API = "https://inventory.roblox.com"


async def get_asset_ownership(
    user_id: int,
    item_type: Literal["asset", "badge", "gamepass", "bundle"],
    asset_id: int,
) -> bool:
    """Query Roblox to see if the given user_id owns the item/asset asset_id.

    Returns:
        bool: True if the user owns the asset/item, false otherwise (or if there is an API error)
    """
    if item_type == "asset":
        item_type = 0
    elif item_type == "gamepass":
        item_type = 1
    elif item_type == "badge":
        item_type = 2
    elif item_type == "bundle":
        item_type = 3

    try:
        response_data, _ = await utils.fetch(
            f"{INVENTORY_API}/v1/users/{user_id}/items/{item_type}/{asset_id}/is-owned",
            return_data=utils.ReturnType.TEXT,
        )
    except RobloxAPIError:
        return False

    return response_data == "true"
