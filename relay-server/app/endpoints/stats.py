from typing import TypedDict
from ..base import RelayEndpoint
from ..redis import RedisRelayRequest


class Response(TypedDict):
    test: bool


class InformationEndpoint(RelayEndpoint):
    def __init__(self):
        super().__init__("REQUEST_STATS")

    async def handle(self, request: RedisRelayRequest) -> Response:
        # await request.respond(
        #     {
        #         # "started_at": started_at.isoformat() if started_at else None,
        #         # "shard": client.shard_id,
        #         # "guild_ids": [guild.id for guild in client.guilds],
        #         # "cpu_usage": psutil.cpu_percent(),
        #         # "ram_usage": psutil.virtual_memory().percent,
        #         "test": True
        #     },
        # )

        return Response(test=True, success=True)
