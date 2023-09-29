import psutil

from resources.ipc import RelayEndpoint, RelayRequest
from resources.secrets import CLUSTER_ID
from resources.modules.discord import started_at, client


if CLUSTER_ID:

    class InformationEndpoint(RelayEndpoint):
        def __init__(self):
            super().__init__(f"CLUSTER_{CLUSTER_ID}")

        async def handle(self, request: RelayRequest):
            await request.respond(
                {
                    "started_at": started_at.isoformat() if started_at else None,
                    "shard": client.shard_id,
                    "guild_ids": [guild.id for guild in client.guilds],
                    "cpu_usage": psutil.cpu_percent(),
                    "ram_usage": psutil.virtual_memory().percent,
                },
            )
