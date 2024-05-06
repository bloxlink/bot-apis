import time
from datetime import timedelta
from bloxlink_lib import get_node_id, BaseModel
from ..base import RelayEndpoint
from ..redis import RedisRelayRequest
from ..bloxlink import bloxlink
from ..types import Response


class StatsResponse(Response):
    """Response from the stats command."""

    node_id: int
    guild_count: int
    user_count: int
    uptime: timedelta


class InformationEndpoint(RelayEndpoint):
    """An endpoint for getting information about the current node."""

    def __init__(self):
        super().__init__("REQUEST_STATS")

    async def handle(self, request: RedisRelayRequest) -> StatsResponse:
        return StatsResponse(
            node_id=get_node_id(),
            guild_count=len(bloxlink.guilds),
            user_count=len(bloxlink.users),
            uptime=timedelta(seconds=time.time() - bloxlink.started_at)
        )
