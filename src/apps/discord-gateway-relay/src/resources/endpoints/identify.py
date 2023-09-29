from resources.ipc import RelayEndpoint, RelayRequest
from resources.secrets import CLUSTER_ID  # type: ignore[attr-defined]
from resources.modules.discord import client


if CLUSTER_ID:

    class IdentifyEndpoint(RelayEndpoint):
        def __init__(self):
            super().__init__("IDENTIFY")

        async def handle(self, request: RelayRequest):
            target_cluster_id = request.payload.get("target_cluster_id", None)
            if target_cluster_id and target_cluster_id != CLUSTER_ID:
                # Do not respond, this request wasn't intended for this cluster.
                return

            # We simply acknowledge our presence with our ID.
            await request.respond({"cluster_id": CLUSTER_ID})
