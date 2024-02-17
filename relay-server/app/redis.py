import importlib
import os
import asyncio
import time
import json
import logging
from typing import Optional

from bloxlink_lib import find, load_modules
from bloxlink_lib.database import redis
from .base import RELAY_ENDPOINTS, RelayEndpoint, RelayRequest, RelayPath
from .bloxlink import bloxlink


redis_pubsub = redis.pubsub()
redis_heartbeat_task = None

background_tasks = set()


class RedisRelayRequest(RelayRequest):
    """A request object for the Redis relay system."""

    def __init__(self, received_at: int, nonce: Optional[str], payload: dict | None):
        super().__init__(received_at, nonce, payload)

    async def respond(self, data: dict | list, *, channel: Optional[str] = None):
        if not channel and not self.nonce:
            # System is intended to use n nonce (operation id) to track responses.
            # If not, a channel should be specified.
            raise ValueError("Channel must be provided if lacking nonce.")

        working_channel = channel or f"REPLY:{self.nonce}"

        try:
            response_data = json.dumps({"nonce": self.nonce, "data": data, "cluster_id": bloxlink.node_id})
            await redis.publish(working_channel, response_data)

            published_at = time.time_ns()
            logging.info(
                f"Published response to {working_channel} in {(published_at - self.received_at) / 1000000:.3f}ms"
            )

        except TypeError as e:
            logging.error(
                "An error was encountered converting to JSON for "
                f"request {self.nonce} on {working_channel}: {e} by {data}",
            )

        except Exception as e: # pylint: disable=broad-except
            logging.error(
                "There was a general error publishing a response for "
                f"request {self.nonce} on {working_channel}: {e}"
            )


def discover_endpoints() -> list[RelayEndpoint]:
    """Discovers all endpoints in the endpoints directory."""

    discovered_endpoints: list[RelayEndpoint] = []
    endpoint_modules = load_modules("app/endpoints", starting_path="./relay-server/")

    for endpoint_module in endpoint_modules:
        for endpoint_class_name in filter(
            lambda n: n != "RelayEndpoint" and n.lower().endswith("endpoint"), dir(endpoint_module)
        ):
            endpoint_class = getattr(endpoint_module, endpoint_class_name)

            if not issubclass(endpoint_class, RelayEndpoint):
                continue

            discovered_endpoints.append(endpoint_class())

    return discovered_endpoints


async def handle_message(message: dict[str, str]):
    """Handles a message from the pubsub channel."""

    received_at = time.time_ns()

    channel = RelayPath(message["channel"])
    endpoint_name = channel[0]

    data: dict
    nonce: str
    payload: dict | None

    try:
        # System-defined data (nonce)
        data = json.loads(message["data"])
        nonce = data.pop("nonce", "")

        # User-defined data.
        payload = data.get("data", {})

    except Exception as ex: # pylint: disable=broad-except
        logging.error(f"Received malformed request: {ex.__class__.__name__} {ex}")
        return

    endpoint: RelayEndpoint | None = find(lambda e: e.path == endpoint_name, RELAY_ENDPOINTS)

    if not endpoint:
        logging.warning("Ignored request, no suitable endpoints.")
        return

    try:
        request = RedisRelayRequest(received_at, nonce, payload)

        await asyncio.wait_for(endpoint.handle(request), timeout=2)

    except TimeoutError:
        logging.error(f"Endpoint execution: {channel} exceeded process time!")
    # TODO: Catch few types of redis exceptions

    except redis.ConnectionError:
        pass

    except Exception as ex: # pylint: disable=broad-except
        logging.error(f"Endpoint {channel}: {ex.__class__.__name__} {ex}")



async def run():
    """Runs the Redis pubsub listener."""

    try:
        RELAY_ENDPOINTS.extend(discover_endpoints())
    except Exception as ex:
        logging.error(f"Failed to load endpoints: {ex}")
        raise SystemExit(ex) from ex

    # Subscribe to channels, including ones used to interact with relay endpoints.
    endpoint_channels = [str(e.path) for e in RELAY_ENDPOINTS]
    logging.info(f"Connecting to pubsub channels: {endpoint_channels}")

    await redis_pubsub.subscribe(*endpoint_channels)

    logging.info("Listening for messages.")

    while True:
        async for message in redis_pubsub.listen():
            if message and message["type"] == "message":
                handler = asyncio.create_task(handle_message(message))
                background_tasks.add(handler)
                handler.add_done_callback(background_tasks.discard)

asyncio.create_task(run())
